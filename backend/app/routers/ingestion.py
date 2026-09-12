import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.deps import get_current_user
from app.database import get_db
from app.services.gmail_service import get_auth_url, handle_callback, ingest_emails, is_authenticated
from app.services.email_connector import (
    get_email_config,
    save_email_config,
    test_imap_connection,
    fetch_live_headers,
    download_raw_eml,
)
from app.services.email_etl_service import parse_eml_file
from app.models.classification import IngestionJob, RawEmailStaging
from app.models.case import Case
from app.models.document import Document
from app.models.event import Event
from app.models.time_entry import Voucher

router = APIRouter()


# --- Request/Response Schemas ---
class GmailConfigRequest(BaseModel):
    email_address: str
    app_password: str
    imap_host: Optional[str] = "imap.gmail.com"
    imap_port: Optional[int] = 993


class TestConnectionRequest(BaseModel):
    email_address: str
    app_password: str
    imap_host: Optional[str] = "imap.gmail.com"
    imap_port: Optional[int] = 993


class StageEmailsRequest(BaseModel):
    message_ids: List[str]
    folder: Optional[str] = "INBOX"


class HumanVerifyCommitRequest(BaseModel):
    case_number: Optional[str] = None
    court: Optional[str] = None
    category: Optional[str] = None
    defendant_name: Optional[str] = None
    hearing_datetime: Optional[str] = None
    warrant_number: Optional[str] = None
    amount_paid: Optional[float] = None
    notes: Optional[str] = None
    verified_by: Optional[str] = "Kimbel Brandon, Esq."


class GmailCallbackRequest(BaseModel):
    code: str


class GmailIngestRequest(BaseModel):
    query: str
    case_id: Optional[int] = None
    max_results: int = 50


# --- IMAP / Google for Business Endpoints ---

@router.get("/gmail/config")
async def get_gmail_connector_config(current_user: dict = Depends(get_current_user)):
    """Retrieve current email connection configuration with masked password."""
    cfg = get_email_config()
    pw = cfg.get("app_password", "")
    masked_pw = ("*" * (len(pw) - 4) + pw[-4:]) if len(pw) >= 4 else ("****" if pw else "")
    return {
        "email_address": cfg.get("email_address"),
        "app_password_masked": masked_pw,
        "imap_host": cfg.get("imap_host", "imap.gmail.com"),
        "imap_port": cfg.get("imap_port", 993),
        "is_connected": cfg.get("is_connected", False),
        "last_connected_at": cfg.get("last_connected_at"),
    }


@router.post("/gmail/config")
async def update_gmail_connector_config(
    body: GmailConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save email and Google App Password configuration."""
    clean_pw = body.app_password.replace(" ", "").strip()
    updated = save_email_config({
        "email_address": body.email_address.strip(),
        "app_password": clean_pw,
        "imap_host": body.imap_host,
        "imap_port": body.imap_port,
    })
    return {"status": "saved", "email_address": updated["email_address"]}


@router.post("/gmail/test")
async def test_gmail_connector_connection(
    body: TestConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Test live IMAP/SSL handshake with Google Mail servers."""
    result = test_imap_connection(
        email_address=body.email_address,
        app_password=body.app_password,
        host=body.imap_host or "imap.gmail.com",
        port=body.imap_port or 993,
    )
    return result


@router.get("/gmail/headers")
async def get_live_gmail_headers(
    limit: int = Query(default=30, ge=1, le=100),
    folder: str = Query(default="INBOX"),
    search_filter: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Fetch live email headers (Subject, From, Date, Case # tag) directly from mailbox."""
    headers = fetch_live_headers(folder=folder, limit=limit, search_filter=search_filter)
    return {
        "count": len(headers),
        "headers": headers,
    }


@router.post("/gmail/stage")
async def stage_emails_for_verification(
    body: StageEmailsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Download complete RFC 822 MIME byte stream (.eml) into semi-permanent storage,
    execute rule-based ETL parser, and create RawEmailStaging records awaiting Human Review.
    """
    staged_records = []

    for msg_id in body.message_ids:
        # 1. Capture raw .eml bytes to disk
        download_res = download_raw_eml(msg_id, folder=body.folder or "INBOX")
        file_path = download_res.get("file_path")
        size_bytes = download_res.get("size_bytes", 0)

        # 2. Parse RFC 822 .eml with ETL engine
        parsed = parse_eml_file(file_path)
        extracted = parsed.get("extracted", {})

        subject = parsed.get("subject", "No Subject")
        from_addr = parsed.get("from", "")
        to_addr = parsed.get("to", "")
        date_str = parsed.get("date", "")
        filter_tag = extracted.get("category", "UNCATEGORIZED")

        # 3. Check if already staged (by message_id or file_path)
        existing = await db.execute(
            select(RawEmailStaging).where(
                (RawEmailStaging.message_id == msg_id) | (RawEmailStaging.file_path == file_path)
            )
        )
        record = existing.scalars().first()

        extracted_json = json.dumps({
            "parsed_headers": {
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date_str,
            },
            "extracted": extracted,
            "attachments_count": len(parsed.get("attachments", [])),
            "plain_preview": parsed.get("plain_body", "")[:400],
        })

        if record:
            record.subject = subject
            record.sender = from_addr
            record.recipient = to_addr
            record.date_sent = date_str
            record.raw_size_bytes = size_bytes
            record.filter_tag = filter_tag
            record.etl_status = "PARSED"
            record.extracted_data_json = extracted_json
        else:
            record = RawEmailStaging(
                message_id=msg_id,
                sender=from_addr,
                recipient=to_addr,
                subject=subject,
                date_sent=date_str,
                file_path=file_path,
                raw_size_bytes=size_bytes,
                filter_tag=filter_tag,
                etl_status="PARSED",
                extracted_data_json=extracted_json,
            )
            db.add(record)

        staged_records.append(record)

    await db.commit()
    return {
        "status": "success",
        "staged_count": len(staged_records),
        "message": f"Successfully staged and parsed {len(staged_records)} raw RFC 822 email(s) for Human Verification.",
    }


# --- Human Verification Board Endpoints ---

@router.get("/staged")
async def list_staged_emails(
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all staged emails awaiting or finished human verification."""
    query = select(RawEmailStaging).order_by(RawEmailStaging.id.desc())
    if status:
        query = query.where(RawEmailStaging.etl_status == status)

    res = await db.execute(query)
    items = res.scalars().all()

    output = []
    for item in items:
        try:
            extracted_meta = json.loads(item.extracted_data_json) if item.extracted_data_json else {}
        except Exception:
            extracted_meta = {}

        output.append({
            "id": item.id,
            "message_id": item.message_id,
            "sender": item.sender,
            "recipient": item.recipient,
            "subject": item.subject,
            "date_sent": item.date_sent,
            "file_path": item.file_path,
            "raw_size_bytes": item.raw_size_bytes,
            "filter_tag": item.filter_tag,
            "etl_status": item.etl_status,
            "extracted_data": extracted_meta,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            "verified_by": item.verified_by,
        })
    return output


@router.get("/staged/{staged_id}")
async def get_staged_email_detail(
    staged_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve full raw RFC 822 email content and ETL proposal for side-by-side human review."""
    res = await db.execute(select(RawEmailStaging).where(RawEmailStaging.id == staged_id))
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Staged email not found")

    parsed_data = {}
    if item.file_path and os.path.exists(item.file_path):
        parsed_data = parse_eml_file(item.file_path)

    try:
        extracted_meta = json.loads(item.extracted_data_json) if item.extracted_data_json else {}
    except Exception:
        extracted_meta = {}

    return {
        "id": item.id,
        "message_id": item.message_id,
        "sender": item.sender,
        "recipient": item.recipient,
        "subject": item.subject,
        "date_sent": item.date_sent,
        "file_path": item.file_path,
        "raw_size_bytes": item.raw_size_bytes,
        "filter_tag": item.filter_tag,
        "etl_status": item.etl_status,
        "extracted_meta": extracted_meta,
        "parsed_email": parsed_data,
        "verified_at": item.verified_at,
        "verified_by": item.verified_by,
    }


@router.post("/staged/{staged_id}/commit")
async def commit_staged_email_verified(
    staged_id: int,
    body: HumanVerifyCommitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Mandatory Human Verification Commit Action.
    Applies approved structured data to Cases, Events, Documents, and Vouchers.
    Marks the raw staging record as VERIFIED_COMMITTED.
    """
    res = await db.execute(select(RawEmailStaging).where(RawEmailStaging.id == staged_id))
    staged_item = res.scalars().first()
    if not staged_item:
        raise HTTPException(status_code=404, detail="Staged email not found")

    # Read raw email body text
    parsed_data = {}
    if staged_item.file_path and os.path.exists(staged_item.file_path):
        parsed_data = parse_eml_file(staged_item.file_path)

    body_text = parsed_data.get("plain_body") or parsed_data.get("html_body") or staged_item.subject

    # 1. Match or associate Case
    target_case = None
    if body.case_number:
        case_res = await db.execute(select(Case).where(Case.case_number == body.case_number))
        target_case = case_res.scalars().first()

    # 2. Perform Category-Specific DB Updates
    committed_actions = []

    # Category A: County Auditor Disbursement Warrant -> Mark Voucher PAID
    if body.category == "COUNTY_AUDITOR_WARRANT":
        voucher_query = select(Voucher)
        if target_case:
            voucher_query = voucher_query.where(Voucher.case_id == target_case.id)
        
        v_res = await db.execute(voucher_query)
        vouchers = v_res.scalars().all()
        
        # Pick the most relevant voucher (APPROVED or newest)
        matched_v = next((v for v in vouchers if v.status in ("APPROVED", "UNBILLED")), (vouchers[0] if vouchers else None))
        if matched_v:
            matched_v.status = "PAID"
            matched_v.warrant_number = body.warrant_number or f"WARR-{staged_id}"
            if body.amount_paid:
                matched_v.amount_paid = body.amount_paid
                matched_v.amount_approved = body.amount_paid
            matched_v.paid_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            committed_actions.append(f"Voucher #{matched_v.voucher_number} updated to PAID (Warrant #{matched_v.warrant_number})")

    # Category B: Hearing Notice -> Insert Event on Court Docket
    if body.category == "HEARING_NOTICE" and target_case:
        evt = Event(
            case_id=target_case.id,
            event_type="hearing",
            title=f"Court Hearing ({body.court or target_case.court})",
            description=f"{staged_item.subject}\nNotes: {body.notes or 'Court coordinator notice'}",
            event_date=body.hearing_datetime[:10] if body.hearing_datetime else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        db.add(evt)
        committed_actions.append(f"Hearing event scheduled on docket for Case #{target_case.case_number}")

    # Category C: Order Appointing Counsel -> Verify Case Appointment Status
    if body.category == "APPOINTMENT_ORDER" and target_case:
        target_case.has_appointment_order = True
        target_case.appointment_status = "VERIFIED_ON_DOCKET"
        target_case.appointment_order_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        committed_actions.append(f"Order Appointing Counsel marked VERIFIED_ON_DOCKET for Case #{target_case.case_number}")

    # 3. Create permanent Document record linked to case
    doc = Document(
        case_id=target_case.id if target_case else None,
        client_id=target_case.client_id if target_case else None,
        filename=f"{staged_item.date_sent[:10] if staged_item.date_sent else 'email'}_{staged_item.subject[:40].replace('/', '-')}.eml",
        doc_type="email",
        source="gmail_verified",
        content_text=body_text[:5000],
        classification_label=body.category.lower() if body.category else "court_notice",
        classification_confidence=1.0,  # Human verified
    )
    db.add(doc)
    committed_actions.append("Permanent email document linked in case archive")

    # 4. Mark staging record as VERIFIED_COMMITTED
    staged_item.etl_status = "VERIFIED_COMMITTED"
    staged_item.verified_at = datetime.now(timezone.utc)
    staged_item.verified_by = body.verified_by or "Kimbel Brandon, Esq."

    await db.commit()

    return {
        "status": "committed",
        "staged_id": staged_id,
        "case_number": body.case_number,
        "committed_actions": committed_actions,
        "verified_by": staged_item.verified_by,
        "verified_at": staged_item.verified_at.isoformat(),
    }


@router.post("/staged/{staged_id}/reject")
async def reject_staged_email(
    staged_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reject or archive a staged email that does not contain relevant court or voucher data."""
    res = await db.execute(select(RawEmailStaging).where(RawEmailStaging.id == staged_id))
    staged_item = res.scalars().first()
    if not staged_item:
        raise HTTPException(status_code=404, detail="Staged email not found")

    staged_item.etl_status = "REJECTED"
    staged_item.verified_at = datetime.now(timezone.utc)
    staged_item.verified_by = "Rejected by User"
    await db.commit()

    return {"status": "rejected", "staged_id": staged_id}


# --- Legacy OAuth & Job Polling Support ---

@router.get("/gmail/status")
async def gmail_status(current_user: dict = Depends(get_current_user)):
    """Check whether Gmail connector is configured."""
    cfg = get_email_config()
    return {
        "authenticated": cfg.get("is_connected", False) or is_authenticated(),
        "auth_mode": cfg.get("auth_mode", "app_password"),
        "email_address": cfg.get("email_address"),
    }


@router.get("/gmail/auth-url")
async def gmail_auth_url(current_user: dict = Depends(get_current_user)):
    """Return Google OAuth URL."""
    return {"auth_url": get_auth_url()}


@router.post("/gmail/callback")
async def gmail_callback(
    body: GmailCallbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Exchange OAuth code for token."""
    return handle_callback(body.code)


@router.post("/gmail/ingest")
async def start_gmail_ingest(
    body: GmailIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Start legacy background Gmail ingestion job."""
    job_id = await ingest_emails(db, body.query, body.max_results, body.case_id)
    return {"job_id": job_id, "status": "started"}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Poll ingestion job status."""
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "source_type": job.source_type,
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "records_found": job.records_found,
        "records_saved": job.records_saved,
        "error_log": job.error_log,
    }


@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List recent ingestion jobs."""
    result = await db.execute(
        select(IngestionJob).order_by(IngestionJob.id.desc()).limit(20)
    )
    jobs = result.scalars().all()
    return [
        {
            "job_id": j.id,
            "source_type": j.source_type,
            "status": j.status,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "records_found": j.records_found,
            "records_saved": j.records_saved,
        }
        for j in jobs
    ]


@router.post("/csv")
async def ingest_csv(current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="CSV import coming in v0.2")
