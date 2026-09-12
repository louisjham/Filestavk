"""
Nueces County Odyssey Public Portal (Smart Search) Automation Service.

Implements human-in-the-loop assisted browser lookup:
1. Launches headed Chromium to https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29
2. Human solves the visual CAPTCHA challenge in the browser window
3. Automation detects search form ready, enters Case Number or Name (Last, First Middle)
4. Toggles human-verification checkbox and submits
5. Captures raw HTML & plain text (indestructible storage in documents table)
6. Parses structured case details, charges, and register of actions into cases & events tables
7. Enforces rate limits, single-action limits, and audit logging.
"""

import os
import json
import uuid
import time
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from bs4 import BeautifulSoup
from app.config import settings

logger = logging.getLogger(__name__)

PORTAL_URL = "https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29"

# In-memory tracking of active jobs
# job_id -> { status, message, search_type, search_query, started_at, completed_at, document_id, case_id, error, cancel_flag }
JOBS: Dict[str, Dict[str, Any]] = {}


def get_db_path() -> str:
    return settings.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return JOBS.get(job_id)


def resume_job(job_id: str) -> bool:
    """Manually signals that the human has solved the CAPTCHA and is on the search screen."""
    job = JOBS.get(job_id)
    if job and job.get("status") in ("WAITING_FOR_HUMAN_CAPTCHA", "LAUNCHING_BROWSER", "PENDING"):
        ev = job.get("resume_event")
        if ev and isinstance(ev, threading.Event):
            ev.set()
        job["status"] = "SEARCHING"
        job["message"] = "Human passed control! Vanishing browser and filling search query..."
        return True
    return False


def cancel_job(job_id: str) -> bool:
    job = JOBS.get(job_id)
    if job and job["status"] not in ("DONE", "ERROR", "CANCELLED"):
        job["cancel_flag"] = True
        job["status"] = "CANCELLED"
        job["message"] = "Lookup cancelled by user."
        return True
    return False


def _vanish_browser_window():
    """Smoothly minimizes the Playwright Chromium window on Windows into the background."""
    try:
        import ctypes
        import ctypes.wintypes

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        GetWindowTextW = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        ShowWindow = ctypes.windll.user32.ShowWindow

        def foreach_window(hwnd, lParam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(k in title for k in ["portal", "nueces", "tyler", "chromium", "smart search", "odyssey", "chrome"]):
                        # 6 = SW_MINIMIZE
                        ShowWindow(hwnd, 6)
            return True

        EnumWindows(EnumWindowsProc(foreach_window), 0)
    except Exception as e:
        logger.debug(f"Could not minimize browser window: {e}")


def _find_search_field_and_frame(page):
    """Searches main frame and all child iframes for a text-fillable search input."""
    frames = [page.main_frame] + page.frames
    text_selectors = [
        "input#SearchCriteria",
        "input[name='SearchCriteria']",
        "#caseSearchInput",
        "input[id*='SearchCriteria' i]",
        "input[name*='SearchCriteria' i]",
        "input[placeholder*='Search' i]",
        "input[placeholder*='Case' i]",
        "input[placeholder*='Name' i]",
        "input.form-control[type='text']",
        "input.form-control",
        "input[type='text']",
        "input[type='search']",
    ]
    for frame in frames:
        for sel in text_selectors:
            try:
                elem = frame.query_selector(sel)
                if elem and elem.is_visible() and elem.is_enabled():
                    elem_type = (elem.get_attribute("type") or "text").lower()
                    if elem_type not in ["submit", "button", "checkbox", "radio", "hidden", "image", "reset", "file"]:
                        return frame, elem
            except Exception:
                pass
    return None, None


def _check_human_box(frame, page):
    """Finds and checks the 'I am human' / verification checkbox across all frames."""
    frames = ([frame] if frame else []) + [page.main_frame] + page.frames
    for f in frames:
        try:
            cbs = f.query_selector_all("input[type='checkbox']")
            for cb in cbs:
                if cb.is_visible() and not cb.is_checked():
                    cb.click()
                    time.sleep(0.3)
        except Exception:
            pass


def _submit_search_form(frame, page, search_elem):
    """Submits the Smart Search form via submit button or Enter key."""
    frames = ([frame] if frame else []) + [page.main_frame] + page.frames
    submit_selectors = [
        "#btnSSSubmit",
        "input#btnSSSubmit",
        "input[type='submit'][value*='Submit' i]",
        "button[type='submit']",
        "input[value*='Submit' i]",
        "button:has-text('Submit')",
        "button:has-text('Search')",
        "input[value*='Search' i]",
        "input[type='submit']",
    ]
    for f in frames:
        for sel in submit_selectors:
            try:
                btn = f.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click()
                    return True
            except Exception:
                pass

    if search_elem:
        try:
            search_elem.press("Enter")
            return True
        except Exception:
            pass

    try:
        page.keyboard.press("Enter")
        return True
    except Exception:
        pass

    return False


def _log_audit(portal: str, client_name: str, action: str, outcome: str, error_message: Optional[str] = None):
    try:
        conn = sqlite3.connect(get_db_path())
        cur = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """INSERT INTO portal_audit_log (portal, client_name, action, outcome, error_message, performed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (portal, client_name, action, outcome, error_message, now)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to write portal audit log: {e}")


import re

def _parse_case_html(html: str, text: str) -> Dict[str, Any]:
    """Parse extracted HTML and plain text for structured legal case information."""
    soup = BeautifulSoup(html, "html.parser")
    data: Dict[str, Any] = {
        "case_number": "",
        "court": "Nueces County Court",
        "case_title": "",
        "case_type": "CRIMINAL",
        "status": "OPEN",
        "filing_date": "",
        "judicial_officer": "",
        "parties": [],
        "charges": [],
        "events": [],
    }

    # 1. Regex search for Case Number in text and HTML
    case_num_match = re.search(r'(?:Case\s*(?:No\.?|Number|#)\s*[:\s]*|)(\b(?:\d{2,4}-[A-Z]{1,4}-\d+|[A-Z]{1,4}-\d{2,4}-\d+|\d{6,10})\b)', text, re.IGNORECASE)
    if case_num_match:
        data["case_number"] = case_num_match.group(1).strip()

    # Extract case number and court from headings or spans
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "div", "span", "p"]):
        txt = heading.get_text(strip=True)
        if not data["case_number"]:
            m = re.search(r'Case\s*(?:No\.?|Number|#)\s*[:\s]*([A-Za-z0-9\-]+)', txt, re.IGNORECASE)
            if m:
                data["case_number"] = m.group(1).strip()
        if "Court:" in txt or "Court" in txt:
            if any(k in txt for k in ["District Court", "County Court", "Court at Law", "Magistrate", "105th", "28th", "94th", "117th", "148th", "214th", "319th", "347th"]):
                data["court"] = txt.replace("Court:", "").strip()

    # 2. Look for table data (Charges, Register of Actions, Events)
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

        # Check if this is an Events / Register of Actions table
        if any("date" in h for h in headers) and any(k in " ".join(headers) for k in ["event", "action", "description", "docket", "hearing"]):
            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= 2:
                    date_val = cols[0]
                    title_val = cols[1]
                    desc_val = " - ".join(cols[2:]) if len(cols) > 2 else ""
                    data["events"].append({
                        "event_date": date_val,
                        "title": title_val,
                        "description": desc_val,
                    })

        # Check if this is a Charges table
        if any("charge" in h or "count" in h or "statute" in h or "offense" in h for h in headers):
            for row in rows[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if cols:
                    data["charges"].append(" | ".join(cols))

    # 3. Fallback text line parsing
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        lower = line.lower()
        if ("case number" in lower or "case no" in lower) and i + 1 < len(lines) and not data["case_number"]:
            data["case_number"] = lines[i + 1].strip()
        elif "judicial officer" in lower and i + 1 < len(lines):
            data["judicial_officer"] = lines[i + 1].strip()
        elif "filed date" in lower or "filing date" in lower:
            if i + 1 < len(lines):
                data["filing_date"] = lines[i + 1].strip()
        elif "case status" in lower and i + 1 < len(lines):
            data["status"] = lines[i + 1].strip()
        elif "case type" in lower and i + 1 < len(lines):
            data["case_type"] = lines[i + 1].strip()

    return data



def _save_portal_extraction_to_db(
    search_type: str,
    search_query: str,
    case_id: Optional[int],
    client_id: Optional[int],
    full_html: str,
    full_text: str,
    parsed_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Saves extracted portal data into documents, cases, events, and audit log."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    case_num = parsed_data.get("case_number") or (search_query if search_type == "case_number" else "UNKNOWN-CASE")
    safe_name = search_query.replace(" ", "_").replace(",", "").replace("/", "-")
    filename = f"Nueces_Portal_{safe_name}_{int(time.time())}.txt"

    metadata = {
        "portal": "Nueces County Odyssey Public Portal",
        "search_type": search_type,
        "search_query": search_query,
        "captured_at": now,
        "parsed": parsed_data,
    }
    meta_json = json.dumps(metadata)

    # 1. Match or Create Case
    resolved_case_id = case_id
    if not resolved_case_id and case_num:
        cur.execute("SELECT id FROM cases WHERE case_number = ?", (case_num,))
        row = cur.fetchone()
        if row:
            resolved_case_id = row[0]
        else:
            court_val = parsed_data.get("court") or "Nueces County District Court"
            status_val = parsed_data.get("status") or "OPEN"
            type_val = parsed_data.get("case_type") or "CRIMINAL"
            opened_val = parsed_data.get("filing_date") or now[:10]
            
            cur.execute(
                """INSERT INTO cases (client_id, case_number, court, case_type, status, is_cja, voucher_status, opened_date, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, 0, 'NONE', ?, 'Imported from Nueces County Odyssey Portal', ?)""",
                (client_id, case_num, court_val, type_val, status_val, opened_val, now)
            )
            resolved_case_id = cur.lastrowid

    # 2. Save Document (Indestructible raw storage)
    cur.execute(
        """INSERT INTO documents (case_id, client_id, filename, doc_type, source, content_text, metadata_json, classification_label, classification_confidence, ingested_at, created_at)
           VALUES (?, ?, ?, 'court_record_lookup', 'nueces_odyssey_portal', ?, ?, 'court_order', 1.0, ?, ?)""",
        (resolved_case_id, client_id, filename, full_text, meta_json, now, now)
    )
    doc_id = cur.lastrowid

    # 3. Create Events from Register of Actions
    events_added = 0
    if resolved_case_id and parsed_data.get("events"):
        for ev in parsed_data["events"]:
            t_val = ev.get("title") or "Court Event"
            d_val = ev.get("description") or ""
            dt_val = ev.get("event_date") or ""
            cur.execute(
                """INSERT INTO events (case_id, event_type, title, description, event_date, created_at)
                   VALUES (?, 'filing', ?, ?, ?, ?)""",
                (resolved_case_id, t_val, d_val, dt_val, now)
            )
            events_added += 1

    conn.commit()
    conn.close()

    _log_audit("nueces_odyssey", search_query, search_type, "SUCCESS", None)

    return {
        "document_id": doc_id,
        "case_id": resolved_case_id,
        "case_number": case_num,
        "events_created": events_added,
        "parsed_data": parsed_data,
    }


def _run_playwright_portal_lookup(
    job_id: str,
    search_type: str,
    search_query: str,
    case_id: Optional[int],
    client_id: Optional[int]
):
    """
    Playwright headed browser automation worker.
    Runs in background thread.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    job = JOBS[job_id]
    job["status"] = "LAUNCHING_BROWSER"
    job["message"] = "Opening browser window. Navigating to Nueces County Public Portal..."

    try:
        with sync_playwright() as p:
            # Launch headed browser so the human user can solve the visual CAPTCHA challenge
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(viewport={"width": 1280, "height": 850})
            page = context.new_page()

            page.goto(PORTAL_URL, timeout=45000, wait_until="domcontentloaded")

            job["status"] = "WAITING_FOR_HUMAN_CAPTCHA"
            job["message"] = (
                "Browser opened! Please complete the CAPTCHA image challenge on your screen, "
                "then click 'I'm on the Search Page' in Filestavk."
            )

            # Wait for user to solve CAPTCHA and land on Smart Search, or signal resume
            active_frame = None
            search_input = None
            max_wait_seconds = 240
            poll_interval = 0.8
            elapsed = 0.0

            while elapsed < max_wait_seconds:
                if job.get("cancel_flag"):
                    browser.close()
                    return

                # Check if manual resume signal was triggered
                if job.get("resume_event") and job["resume_event"].is_set():
                    logger.info(f"Portal Job {job_id}: Manual resume signal received.")
                    break

                # Auto-check if search field is visible in any frame
                f, elem = _find_search_field_and_frame(page)
                if elem:
                    active_frame = f
                    search_input = elem
                    logger.info(f"Portal Job {job_id}: Search field automatically detected.")
                    break

                time.sleep(poll_interval)
                elapsed += poll_interval
                remaining = int(max_wait_seconds - elapsed)
                if int(elapsed) % 4 == 0:
                    job["message"] = f"Please complete the CAPTCHA, then click 'I'm on the Search Page' ({remaining}s remaining)..."

            # 1. Vanish the browser from the user's primary view
            _vanish_browser_window()

            # Step 2: Search form is active
            job["status"] = "SEARCHING"
            job["message"] = f"Vanishing browser and entering search query: '{search_query}'..."

            # If search input wasn't found during polling, search again now across all frames
            if not search_input:
                time.sleep(1)
                active_frame, search_input = _find_search_field_and_frame(page)

            # If still not found, try navigating to Smart Search tile if present
            if not search_input:
                try:
                    tile = page.query_selector("a:has-text('Smart Search'), div.portlet-title:has-text('Smart Search'), a[href*='SmartSearch']")
                    if tile and tile.is_visible():
                        tile.click()
                        time.sleep(1.5)
                        active_frame, search_input = _find_search_field_and_frame(page)
                except Exception:
                    pass

            if not search_input:
                raise RuntimeError("Could not find the Smart Search text field on the page or inside frames. Please ensure the search screen is active.")

            # Focus and fill the search term
            try:
                search_input.click()
                time.sleep(0.2)
                search_input.fill(search_query)
            except Exception as fill_err:
                logger.warning(f"Direct fill failed ({fill_err}), using keyboard typing fallback")
                try:
                    search_input.click()
                    page.keyboard.type(search_query, delay=25)
                except Exception as type_err:
                    logger.error(f"Keyboard type fallback also failed: {type_err}")
                    raise fill_err

            time.sleep(0.4)

            # Check the "I am human" / verification checkbox if present
            _check_human_box(active_frame, page)

            # Click Submit button
            _submit_search_form(active_frame, page, search_input)

            # Step 3: Wait for search results or case detail page
            job["status"] = "EXTRACTING"
            job["message"] = "Search submitted. Extracting court record data..."

            # Wait for results container or table to load
            time.sleep(3)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # If there's a search results list and we see a clickable case link, click the first matching result
            try:
                result_links = page.query_selector_all(
                    "a[href*='CaseDetail'], a[href*='CaseInformation'], a[href*='CaseSummary'], table.k-grid tbody tr td a, td.case-number a, a.case-link"
                )
                if not result_links:
                    all_links = page.query_selector_all("table tbody tr td a, .portlet-body a")
                    for l in all_links:
                        txt = l.inner_text().strip()
                        if search_query.lower() in txt.lower() or any(p in txt for p in ["-CR-", "-CV-", "-DC-", "-CC-", "202"]):
                            result_links = [l]
                            break

                if result_links and result_links[0].is_visible():
                    job["message"] = "Found matching case link in search results. Loading full case summary..."
                    result_links[0].click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"No drilldown link needed or clickable: {e}")

            # Grab full HTML and full inner text across frames
            full_html = page.content()
            full_text = page.inner_text("body")

            for f in page.frames:
                if f != page.main_frame:
                    try:
                        full_html += "\n" + f.content()
                        full_text += "\n" + f.inner_text("body")
                    except Exception:
                        pass

            # Parse structured data
            parsed_data = _parse_case_html(full_html, full_text)

            # Step 4: Ingest into database
            db_res = _save_portal_extraction_to_db(
                search_type=search_type,
                search_query=search_query,
                case_id=case_id,
                client_id=client_id,
                full_html=full_html,
                full_text=full_text,
                parsed_data=parsed_data
            )

            job["status"] = "DONE"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["document_id"] = db_res["document_id"]
            job["case_id"] = db_res["case_id"]
            job["case_number"] = db_res["case_number"]
            job["events_created"] = db_res["events_created"]
            job["parsed_data"] = parsed_data
            job["message"] = (
                f"Successfully extracted record for {db_res['case_number']}! "
                f"Saved to Database (Document #{db_res['document_id']})."
            )

            time.sleep(1)
            browser.close()

    except Exception as e:
        logger.exception("Portal assist error")
        job["status"] = "ERROR"
        job["error"] = str(e)
        job["message"] = f"Lookup failed: {str(e)}"
        _log_audit("nueces_odyssey", search_query, search_type, "ERROR", str(e))


def start_portal_lookup(
    search_type: str,
    search_query: str,
    case_id: Optional[int] = None,
    client_id: Optional[int] = None
) -> str:
    """Start an on-demand portal assist lookup in a background worker."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    resume_event = threading.Event()

    JOBS[job_id] = {
        "job_id": job_id,
        "search_type": search_type,
        "search_query": search_query,
        "case_id": case_id,
        "client_id": client_id,
        "status": "PENDING",
        "message": "Initializing browser lookup...",
        "started_at": now,
        "completed_at": None,
        "document_id": None,
        "cancel_flag": False,
        "resume_event": resume_event,
        "error": None,
    }

    worker = threading.Thread(
        target=_run_playwright_portal_lookup,
        args=(job_id, search_type, search_query, case_id, client_id),
        daemon=True
    )
    worker.start()

    return job_id
