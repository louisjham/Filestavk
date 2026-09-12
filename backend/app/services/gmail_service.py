"""
Gmail ingestion service.

Uses the official Google Gmail API (OAuth 2.0, gmail.readonly scope).
Credentials are loaded from data/gmail_credentials.json.
Token is persisted to data/gmail_token.json after first auth.
"""
import os
import json
import base64
import asyncio
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "../../data/gmail_token.json")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "../../data/gmail_credentials.json")


def _get_client_config() -> dict:
    """Build client config from env vars or credentials file."""
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH) as f:
            return json.load(f)
    # Fall back to env vars
    if settings.gmail_client_id and settings.gmail_client_secret:
        return {
            "installed": {
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.gmail_redirect_uri],
            }
        }
    return {}


def get_auth_url() -> str:
    """Return the Google OAuth authorization URL."""
    config = _get_client_config()
    if not config:
        return "NOT_CONFIGURED"
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=settings.gmail_redirect_uri)
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url


def handle_callback(code: str) -> dict:
    """Exchange auth code for tokens and persist to disk."""
    config = _get_client_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=settings.gmail_redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f)
    return {"status": "connected"}


def is_authenticated() -> bool:
    """Return True if a valid (or refreshable) token exists."""
    return os.path.exists(TOKEN_PATH)


def _load_credentials() -> Optional[Credentials]:
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH) as f:
        data = json.load(f)
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist refreshed token
        data["token"] = creds.token
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f)
    return creds


def _extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            body = _extract_body(part)
            if body:
                return body
    # HTML fallback
    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            # Strip tags very roughly for plain-text storage
            import re
            return re.sub(r"<[^>]+>", " ", raw).strip()
    return ""


def _header(headers: list, name: str) -> str:
    """Extract a named header value."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _run_ingest(job_id: int, query: str, max_results: int, case_id: Optional[int], db_url: str):
    """
    Blocking ingestion run — intended to be called in a background thread.
    Opens its own synchronous DB connection since this runs outside async context.
    """
    import sqlite3
    from urllib.parse import urlparse

    # Parse the SQLite path from the async URL
    db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

    creds = _load_credentials()
    if not creds:
        _update_job(db_path, job_id, "error", error_log="Not authenticated with Gmail")
        return

    _update_job(db_path, job_id, "running")
    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])
        records_found = len(messages)
        records_saved = 0

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        for msg in messages:
            msg_id = msg["id"]
            # Dedup check
            cur.execute(
                "SELECT id FROM documents WHERE source='gmail' AND json_extract(metadata_json,'$.gmail_id')=?",
                (msg_id,),
            )
            if cur.fetchone():
                continue

            full = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            headers = full.get("payload", {}).get("headers", [])
            body = _extract_body(full.get("payload", {}))
            subject = _header(headers, "Subject")
            from_addr = _header(headers, "From")
            to_addr = _header(headers, "To")
            date_str = _header(headers, "Date")
            thread_id = full.get("threadId", "")

            safe_subject = subject[:60].replace("/", "-").replace("\\", "-") or "no-subject"
            filename = f"{date_str[:10] if date_str else 'unknown'}_{safe_subject}.eml"

            meta = json.dumps({
                "gmail_id": msg_id,
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "date": date_str,
                "thread_id": thread_id,
            })

            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                """INSERT INTO documents
                   (case_id, client_id, filename, doc_type, source,
                    content_text, metadata_json, classification_label,
                    classification_confidence, ingested_at, created_at)
                   VALUES (?, NULL, ?, 'email', 'gmail', ?, ?, 'uncategorized', 0.0, ?, ?)""",
                (case_id, filename, body, meta, now, now),
            )
            records_saved += 1

        conn.commit()
        conn.close()
        _update_job(db_path, job_id, "done", found=records_found, saved=records_saved)

    except HttpError as e:
        _update_job(db_path, job_id, "error", error_log=str(e))
    except Exception as e:
        logger.exception("Gmail ingest error")
        _update_job(db_path, job_id, "error", error_log=str(e))


def _update_job(db_path: str, job_id: int, status: str, found: int = 0, saved: int = 0, error_log: str = None):
    import sqlite3
    from datetime import datetime, timezone

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if status in ("done", "error"):
        cur.execute(
            "UPDATE ingestion_jobs SET status=?, completed_at=?, records_found=?, records_saved=?, error_log=? WHERE id=?",
            (status, now, found, saved, error_log, job_id),
        )
    else:
        cur.execute(
            "UPDATE ingestion_jobs SET status=?, started_at=? WHERE id=?",
            (status, now, job_id),
        )
    conn.commit()
    conn.close()


async def ingest_emails(db, query: str, max_results: int, case_id: Optional[int]) -> int:
    """Create an ingestion job record and launch a background thread to run it."""
    from app.models.classification import IngestionJob
    from app.config import settings

    job = IngestionJob(source_type="gmail", status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id

    db_url = settings.database_url
    thread = threading.Thread(
        target=_run_ingest,
        args=(job_id, query, max_results, case_id, db_url),
        daemon=True,
    )
    thread.start()
    return job_id

