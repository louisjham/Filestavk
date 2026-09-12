import csv
import io
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.deps import get_current_user
from app.models.case import Case
from app.models.client import Client
from app.models.time_entry import Voucher

router = APIRouter()

# In-memory store for master spreadsheet rows (populated via paste or CSV/Excel upload)
_SPREADSHEET_STORE: List[dict] = []



class PasteRowsRequest(BaseModel):
    raw_text: str  # Tab-separated, CSV, or line-separated text


class SpreadsheetRow(BaseModel):
    case_number: str
    client_name: Optional[str] = None
    court: Optional[str] = None
    notes: Optional[str] = None


@router.get("/queue")
async def get_spreadsheet_queue(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns master spreadsheet rows cross-referenced against the local SQLite database.
    Provides instant clipboard payloads and flags appointment order status & disposition.
    """
    # Fetch all database cases and vouchers
    res_cases = await db.execute(select(Case, Client).join(Client, Case.client_id == Client.id, isouter=True))
    cases_rows = res_cases.all()

    case_lookup = {}
    for c, cl in cases_rows:
        if c.case_number:
            norm_key = re.sub(r"[^A-Za-z0-9]", "", c.case_number).upper()
            case_lookup[norm_key] = (c, cl)

    res_vouchers = await db.execute(select(Voucher))
    vouchers = res_vouchers.scalars().all()
    voucher_lookup = {}
    for v in vouchers:
        voucher_lookup[v.case_id] = v

    enriched_queue = []
    disposed_count = 0
    missing_appointment_count = 0
    ready_to_bill_count = 0

    for idx, item in enumerate(_SPREADSHEET_STORE):
        case_num = item.get("case_number", "").strip()
        norm_key = re.sub(r"[^A-Za-z0-9]", "", case_num).upper()
        
        db_match = case_lookup.get(norm_key)
        db_case = db_match[0] if db_match else None
        db_client = db_match[1] if db_match else None
        db_voucher = voucher_lookup.get(db_case.id) if db_case else None

        in_db = db_case is not None
        has_appointment_order = db_case.has_appointment_order if db_case else False
        appointment_status = db_case.appointment_status if db_case else "UNKNOWN"
        disposition_type = db_case.disposition_type if db_case else ("DISPOSED" if "disposed" in item.get("notes", "").lower() or "dismiss" in item.get("notes", "").lower() else "ACTIVE")
        is_disposed = disposition_type in ("DISMISSED", "PLEA_GUILTY", "TRIAL_VERDICT", "DEFERRED", "DISPOSED") or (db_case.stage == "DISPOSED" if db_case else False)
        voucher_status = db_voucher.status if db_voucher else (db_case.voucher_status if db_case else "UNBILLED")

        if is_disposed:
            disposed_count += 1
            if voucher_status in ("NONE", "UNBILLED", "DRAFT"):
                ready_to_bill_count += 1

        if not has_appointment_order and is_disposed:
            missing_appointment_count += 1

        enriched_queue.append({
            "id": item.get("id", f"row-{idx+1}"),
            "case_number": case_num,
            "client_name": item.get("client_name") or (db_client.name if db_client else "—"),
            "court": item.get("court") or (db_case.court if db_case else "Nueces County District Court"),
            "judge": db_case.judge if db_case else "—",
            "charge_description": db_case.charge_description if db_case else "—",
            "notes": item.get("notes", ""),
            "in_database": in_db,
            "case_id": db_case.id if db_case else None,
            "has_appointment_order": has_appointment_order,
            "appointment_status": appointment_status,
            "is_disposed": is_disposed,
            "disposition_type": disposition_type,
            "voucher_status": voucher_status,
            "voucher_id": db_voucher.id if db_voucher else None,
            "amount_requested": db_voucher.amount_requested if db_voucher else 1000.0,
            "amount_paid": db_voucher.amount_paid if db_voucher else 0.0,
            "odyssey_url": "https://portal-txnueces.tylertech.cloud/Portal/Home/Dashboard/29",
        })

    return {
        "queue": enriched_queue,
        "total_items": len(enriched_queue),
        "disposed_count": disposed_count,
        "ready_to_bill_count": ready_to_bill_count,
        "missing_appointment_count": missing_appointment_count,
    }


@router.post("/paste-rows")
async def paste_spreadsheet_rows(
    data: PasteRowsRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Parses tab-delimited or CSV rows pasted directly from Excel / Google Sheets or clipboard.
    Appends rows to the master queue.
    """
    lines = [l.strip() for l in data.raw_text.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="No rows provided.")

    new_rows = []
    for idx, line in enumerate(lines):
        # Determine delimiter (tab or comma or semicolon)
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        elif "," in line:
            parts = [p.strip() for p in line.split(",")]
        else:
            parts = [line.strip()]

        case_num = parts[0] if len(parts) > 0 else f"CASE-{idx+1}"
        client_name = parts[1] if len(parts) > 1 else ""
        court = parts[2] if len(parts) > 2 else "Nueces County District Court"
        notes = parts[3] if len(parts) > 3 else ""

        # Skip header rows if detected
        if "case" in case_num.lower() and "number" in case_num.lower():
            continue

        new_rows.append({
            "id": f"row-{len(_SPREADSHEET_STORE) + idx + 1}",
            "case_number": case_num,
            "client_name": client_name,
            "court": court,
            "notes": notes,
        })

    _SPREADSHEET_STORE.extend(new_rows)
    return {
        "success": True,
        "added_count": len(new_rows),
        "total_count": len(_SPREADSHEET_STORE),
        "message": f"Successfully parsed and queued {len(new_rows)} rows from spreadsheet.",
    }


@router.post("/upload")
async def upload_spreadsheet(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Uploads a .csv file and replaces or merges into the spreadsheet queue."""
    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text))
    
    new_rows = []
    for idx, row in enumerate(reader):
        if not row:
            continue
        if idx == 0 and ("case" in row[0].lower() or "cause" in row[0].lower()):
            continue  # Header row
        
        case_num = row[0].strip() if len(row) > 0 else ""
        if not case_num:
            continue
        client_name = row[1].strip() if len(row) > 1 else ""
        court = row[2].strip() if len(row) > 2 else "Nueces County District Court"
        notes = row[3].strip() if len(row) > 3 else ""

        new_rows.append({
            "id": f"row-{idx+1}",
            "case_number": case_num,
            "client_name": client_name,
            "court": court,
            "notes": notes,
        })

    if new_rows:
        global _SPREADSHEET_STORE
        _SPREADSHEET_STORE = new_rows

    return {
        "success": True,
        "loaded_count": len(new_rows),
        "message": f"Loaded {len(new_rows)} cases from {file.filename}.",
    }


@router.get("/export")
async def export_reconciled_spreadsheet(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Exports a CSV file containing the master spreadsheet reconciled with all database statuses,
    appointment orders, disposition dates, and voucher statuses.
    """
    res = await get_spreadsheet_queue(db=db, current_user=current_user)
    queue = res["queue"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Case Number",
        "Client Name",
        "Court",
        "Judge",
        "Charge Description",
        "Appointment Order Verified",
        "Appointment Status",
        "Disposition Status",
        "Voucher Status",
        "Amount Claimed",
        "Amount Paid",
        "Notes"
    ])

    for item in queue:
        writer.writerow([
            item["case_number"],
            item["client_name"],
            item["court"],
            item["judge"],
            item["charge_description"],
            "YES" if item["has_appointment_order"] else "NO / MISSING",
            item["appointment_status"],
            item["disposition_type"],
            item["voucher_status"],
            f"${item['amount_requested']:,.2f}",
            f"${item['amount_paid']:,.2f}",
            item["notes"],
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="nueces_voucher_master_tracker.csv"'},
    )
