"""
Parser for Odyssey Portal Case Summaries & Docket Timelines.
Extracts structured chronological events from Odyssey Portal narratives,
date ranges, docket sheets, and hearing summaries.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def parse_date_to_iso(date_str: str) -> Optional[str]:
    """Converts various date formats (e.g., 'July 5, 2024', '07/05/2024', '2024-07-05') to ISO YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # ISO YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_str)
    if m_iso:
        y, m, d = m_iso.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # MM/DD/YYYY
    m_slash = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", date_str)
    if m_slash:
        m, d, y = m_slash.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # Month DD, YYYY
    m_text = re.match(r"^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$", date_str)
    if m_text:
        mon_name, day, year = m_text.groups()
        mon_num = MONTH_MAP.get(mon_name.lower())
        if mon_num:
            return f"{int(year):04d}-{mon_num:02d}-{int(day):02d}"

    # Month YYYY
    m_my = re.match(r"^([A-Za-z]+)\s+(\d{4})$", date_str)
    if m_my:
        mon_name, year = m_my.groups()
        mon_num = MONTH_MAP.get(mon_name.lower())
        if mon_num:
            return f"{int(year):04d}-{mon_num:02d}-01"

    return None


def infer_event_type(title: str, text: str) -> str:
    """Categorizes docket event into standardized procedural types."""
    t = title.lower()
    combined = f"{title} {text}".lower()

    if "plea" in t or "sentenc" in t:
        return "PLEA_SENTENCING"
    if "counsel" in t or "appoint" in t or "attorney" in t:
        return "APPOINTMENT_ORDER"
    if "abatement" in t or "remand" in t:
        return "ABATEMENT"
    if "appeal" in t:
        return "APPEAL"
    if "incompet" in t or "competency" in t:
        return "COMPETENCY"
    if "arrest" in t or "indict" in t:
        return "ARREST_INDICTMENT"

    if "sentenc" in combined or "plea" in combined or "convict" in combined or "tdcj" in combined:
        return "PLEA_SENTENCING"
    if "abatement" in combined or "remand" in combined:
        return "ABATEMENT"
    if "counsel" in combined or "appoint" in combined or "attorney" in combined or "brandon" in combined:
        return "APPOINTMENT_ORDER"
    if "notice of appeal" in combined or "appellate" in combined or "court of appeals" in combined or "clerk's record" in combined:
        return "APPEAL"
    if "incompet" in combined or "competency" in combined or "psychological" in combined or "rusk state" in combined:
        return "COMPETENCY"
    if "arrest" in combined or "indict" in combined or "magistrate" in combined or "bail" in combined:
        return "ARREST_INDICTMENT"
    if "hearing" in combined or "docket" in combined:
        return "HEARING"
    if "motion" in combined:
        return "MOTION"
    if "order" in combined:
        return "ORDER"
    return "DOCKET_EVENT"


def parse_odyssey_timeline(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parses Odyssey narrative summaries, bullet points, or raw tabular entries
    into structured chronological event objects.
    """
    events = []
    text = raw_text.strip()
    if not text:
        return events

    # Pattern 1: Narrative sections with Date/Range header like:
    # "July 5, 2024 – October 14, 2024 (Arrest & Indictment): Frank A. Roberts was..."
    # or "December 10, 2025 (Plea & Sentencing): The court officially..."
    section_pattern = re.compile(
        r"(?:^|\n\n|\n)(?:[\*\#\-\s]*)"
        r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
        r"(?:\s*[\–\-\—to]+\s*[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})?)"
        r"(?:\s*\(([^)]+)\))?\s*[:\–\-]\s*"
        r"(.*?)(?=(?:\n\n|\n)[\*\#\-\s]*[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    matches = list(section_pattern.finditer(text))
    if matches:
        for m in matches:
            date_range_str = m.group(1).strip()
            parenthetical_title = (m.group(2) or "").strip()
            narrative = m.group(3).strip()

            # Split primary start date
            start_date_raw = re.split(r"[\–\-\—]|\bto\b", date_range_str)[0].strip()
            iso_date = parse_date_to_iso(start_date_raw)

            # Title
            if parenthetical_title:
                title = parenthetical_title
            else:
                first_sent = narrative.split(".")[0]
                title = first_sent[:60] if len(first_sent) > 60 else first_sent

            ev_type = infer_event_type(title, narrative)

            events.append({
                "date_range_display": date_range_str,
                "event_date": iso_date or datetime.now().strftime("%Y-%m-%d"),
                "title": title,
                "event_type": ev_type,
                "description": f"{date_range_str}: {narrative}" if not narrative.startswith(date_range_str) else narrative,
                "raw_snippet": m.group(0).strip(),
            })

    # Pattern 2: Fallback line-by-line tabular parsing if Pattern 1 found no matches
    if not events:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for ln in lines:
            line_match = re.match(
                r"^(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})\s*[:\t|\-–]\s*(.*)$",
                ln
            )
            if line_match:
                d_str, content = line_match.groups()
                iso_d = parse_date_to_iso(d_str)
                parts = content.split(" - ", 1)
                t = parts[0] if len(parts) > 1 else content[:50]
                desc = parts[1] if len(parts) > 1 else content
                events.append({
                    "date_range_display": d_str,
                    "event_date": iso_d or datetime.now().strftime("%Y-%m-%d"),
                    "title": t,
                    "event_type": infer_event_type(t, desc),
                    "description": desc,
                    "raw_snippet": ln,
                })

    # Sort chronologically
    events.sort(key=lambda x: x.get("event_date") or "9999-99-99")
    return events
