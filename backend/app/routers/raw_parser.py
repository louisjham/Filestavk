import re
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.deps import get_current_user
from app.models.case import Case
from app.models.client import Client
from app.models.event import Event
from app.models.time_entry import Voucher, TimeEntry

router = APIRouter()


class ParseRawTextRequest(BaseModel):
    raw_text: str


class CommitRawCaseRequest(BaseModel):
    case_number: str
    client_name: str
    court: str
    judge: Optional[str] = None
    charge_description: Optional[str] = None
    file_date: Optional[str] = None
    offense_date: Optional[str] = None
    has_appointment_order: bool = False
    appointment_order_date: Optional[str] = None
    appointment_status: str = "UNKNOWN"
    disposition_type: Optional[str] = "PENDING"
    disposition_date: Optional[str] = None
    bond_amount: Optional[float] = None
    bond_type: Optional[str] = "SURETY"
    events: List[dict] = []
    auto_create_voucher: bool = True
    notes: Optional[str] = None


NUECES_JUDGES = {
    "28th": ("28th District Court", "Hon. Nanette Hasette"),
    "94th": ("94th District Court", "Hon. Bobby Galvan"),
    "105th": ("105th District Court", "Hon. Jack W. Pulcher"),
    "117th": ("117th District Court", "Hon. Sandra Watts"),
    "148th": ("148th District Court", "Hon. Carlos Valdez"),
    "214th": ("214th District Court", "Hon. Inna Klein"),
    "319th": ("319th District Court", "Hon. David Stith"),
    "347th": ("347th District Court", "Hon. Missy Medary"),
    "court at law no. 1": ("County Court at Law No. 1", "Hon. Todd Robinson"),
    "court at law no 1": ("County Court at Law No. 1", "Hon. Todd Robinson"),
    "court at law #1": ("County Court at Law No. 1", "Hon. Todd Robinson"),
    "court at law no. 2": ("County Court at Law No. 2", "Hon. Lisa Gonzales"),
    "court at law no 2": ("County Court at Law No. 2", "Hon. Lisa Gonzales"),
    "court at law #2": ("County Court at Law No. 2", "Hon. Lisa Gonzales"),
    "court at law no. 3": ("County Court at Law No. 3", "Hon. Deeanne Galvan"),
    "court at law no 3": ("County Court at Law No. 3", "Hon. Deeanne Galvan"),
    "court at law #3": ("County Court at Law No. 3", "Hon. Deeanne Galvan"),
    "court at law no. 4": ("County Court at Law No. 4", "Hon. Mark H. Woerner"),
    "court at law no 4": ("County Court at Law No. 4", "Hon. Mark H. Woerner"),
    "court at law #4": ("County Court at Law No. 4", "Hon. Mark H. Woerner"),
    "court at law no. 5": ("County Court at Law No. 5", "Hon. Timothy J. McCoy"),
    "court at law no 5": ("County Court at Law No. 5", "Hon. Timothy J. McCoy"),
    "court at law #5": ("County Court at Law No. 5", "Hon. Timothy J. McCoy"),
}


def _extract_case_info(text: str) -> dict:
    """Extracts structured fields from raw Tyler Odyssey page text dumps."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full_str = " ".join(lines)

    # 1. Case Number
    case_number = ""
    case_match = re.search(r"(\b\d{2,4}MC-?\d{4,6}[A-Za-z0-9\-]*\b|\d{4}-CR-\d{4,5}-[A-H]|\d{2,4}-\d{4,6}-\d|\b[0-9]{4}CR[0-9]{4,5}\b|CR-\d{4}-\d+)", text, re.IGNORECASE)
    if case_match:
        case_number = case_match.group(1).upper()
    else:
        # Generic fallback
        generic_match = re.search(r"(?:Case Number|Cause No\.?|Case No\.?)\s*:?\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
        if generic_match:
            case_number = generic_match.group(1).upper()

    # 2. Court and Judge
    court = "347th District Court"
    judge = "Hon. Missy Medary"
    for key, (court_name, judge_name) in NUECES_JUDGES.items():
        if key in text.lower():
            court = court_name
            judge = judge_name
            break

    # Look for judicial officer
    judge_match = re.search(r"Judicial Officer\s*:?\s*([A-Za-z\s,\.\-]+?)(?:\n|Court|Date|Case|$)", text, re.IGNORECASE)
    if judge_match:
        raw_judge = judge_match.group(1).strip()
        if len(raw_judge) > 3 and "district" not in raw_judge.lower():
            judge = raw_judge if raw_judge.startswith("Hon.") else f"Hon. {raw_judge}"

    # 3. Defendant / Client Name
    client_name = "Defendant"
    style_match = re.search(r"(?:(?:The\s+)?State of Texas\s+(?:vs?\.?|v\.?)\s+|Defendant\s*:?\s*)([A-Za-z\s,\.\-]+?)(?:\n|DOB|SID|Date|Charge|Attorney|Case|$)", text, re.IGNORECASE)
    if style_match:
        cand = style_match.group(1).strip()
        if cand and len(cand) > 2 and "state" not in cand.lower():
            client_name = cand.title()
    else:
        party_match = re.search(r"Defendant\s+([A-Za-z\s,]+?)(?:\n|DOB|SID|Address|$)", text, re.IGNORECASE)
        if party_match:
            client_name = party_match.group(1).strip().title()

    # 4. File Date
    file_date = ""
    file_match = re.search(r"File Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    if file_match:
        raw_fd = file_match.group(1)
        try:
            file_date = datetime.strptime(raw_fd, "%m/%d/%Y").strftime("%Y-%m-%d")
        except Exception:
            file_date = raw_fd

    # 5. Offense Date & Charge
    charge_description = "Criminal Offense"
    offense_date = ""
    charge_match = re.search(r"(?:Charge|Offense|Count 1)\s*:?\s*([A-Za-z0-9\s\/\-\(\)<>=]+?)(?:\n|Statute|Degree|Level|Date|Arrest|$)", text, re.IGNORECASE)
    if charge_match:
        cand_ch = charge_match.group(1).strip()
        if len(cand_ch) > 4:
            charge_description = cand_ch

    offense_match = re.search(r"Offense Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    if offense_match:
        raw_od = offense_match.group(1)
        try:
            offense_date = datetime.strptime(raw_od, "%m/%d/%Y").strftime("%Y-%m-%d")
        except Exception:
            offense_date = raw_od

    # Degree / Level
    degree = ""
    if "State Jail Felony" in text or "FS" in text or "SJF" in text:
        degree = "State Jail Felony"
    elif "First Degree Felony" in text or "F1" in text:
        degree = "First Degree Felony"
    elif "Second Degree Felony" in text or "F2" in text:
        degree = "Second Degree Felony"
    elif "Third Degree Felony" in text or "F3" in text:
        degree = "Third Degree Felony"
    elif "Class A Misdemeanor" in text or "MA" in text:
        degree = "Class A Misdemeanor"
    elif "Class B Misdemeanor" in text or "MB" in text:
        degree = "Class B Misdemeanor"

    if degree and degree.lower() not in charge_description.lower():
        charge_description = f"{charge_description} ({degree})"

    # 6. Order Appointing Counsel & Docket Events
    has_appointment_order = False
    appointment_order_date = ""
    appointment_status = "MISSING_ORDER"

    if re.search(r"(?:ORDER APPOINTING COUNSEL|APPOINTMENT OF ATTORNEY|ORDER APPOINTING ATTORNEY|APPOINTED ATTORNEY|ACCEPTANCE OF APPOINTMENT)", text, re.IGNORECASE):
        has_appointment_order = True
        appointment_status = "VERIFIED_ON_DOCKET"
        # Find date near appointment
        appt_date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:ORDER APPOINTING|APPOINTMENT|ACCEPTANCE)", text, re.IGNORECASE)
        if appt_date_match:
            try:
                appointment_order_date = datetime.strptime(appt_date_match.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
            except Exception:
                appointment_order_date = appt_date_match.group(1)
        elif file_date:
            appointment_order_date = file_date

    # 7. Disposition Detection
    disposition_type = "PENDING"
    disposition_date = ""
    
    if re.search(r"(?:ORDER OF DISMISSAL|MOTION TO DISMISS GRANTED|DISMISSED|ORDER GRANTING DISMISSAL)", text, re.IGNORECASE):
        disposition_type = "DISMISSED"
    elif re.search(r"(?:JUDGMENT OF CONVICTION|PLEA OF GUILTY|GUILTY PLEA|SENTENCE IMPOSED)", text, re.IGNORECASE):
        disposition_type = "PLEA_GUILTY"
    elif re.search(r"(?:ORDER DEFERRING ADJUDICATION|DEFERRED ADJUDICATION)", text, re.IGNORECASE):
        disposition_type = "DEFERRED"
    elif re.search(r"(?:JURY VERDICT|VERDICT OF NOT GUILTY|ACQUITTAL)", text, re.IGNORECASE):
        disposition_type = "TRIAL_VERDICT"

    disp_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:ORDER OF DISMISSAL|DISMISSAL|JUDGMENT|PLEA|SENTENCE|DISPOSITION)", text, re.IGNORECASE)
    if disp_match:
        try:
            disposition_date = datetime.strptime(disp_match.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
        except Exception:
            disposition_date = disp_match.group(1)
    elif disposition_type != "PENDING" and file_date:
        disposition_date = file_date

    # 8. Bond Info
    bond_amount = 0.0
    bond_type = "SURETY"
    bond_match = re.search(r"Bond Amount\s*:?\s*\$?([0-9,]+(?:\.[0-9]{2})?)", text, re.IGNORECASE)
    if bond_match:
        try:
            bond_amount = float(bond_match.group(1).replace(",", ""))
        except Exception:
            pass

    if re.search(r"PR Bond|Personal Recognizance", text, re.IGNORECASE):
        bond_type = "PR_BOND"
    elif re.search(r"Cash Bond", text, re.IGNORECASE):
        bond_type = "CASH"

    # 9. Extract Events / Register of Actions lines
    extracted_events = []
    event_lines = re.findall(r"(\d{1,2}/\d{1,2}/\d{4})\s+([A-Z\s\/\-\(\)]+?)(?=\d{1,2}/\d{1,2}/\d{4}|$)", text)
    for ev_dt, ev_title in event_lines[:15]:
        clean_title = ev_title.strip()
        if len(clean_title) > 3:
            extracted_events.append({
                "date": ev_dt,
                "title": clean_title,
                "description": f"Extracted from Tyler Odyssey Register of Actions: {clean_title}",
            })

    return {
        "case_number": case_number or "2024-CR-XXXX-D",
        "client_name": client_name,
        "court": court,
        "judge": judge,
        "charge_description": charge_description,
        "file_date": file_date,
        "offense_date": offense_date,
        "has_appointment_order": has_appointment_order,
        "appointment_order_date": appointment_order_date,
        "appointment_status": appointment_status,
        "disposition_type": disposition_type,
        "disposition_date": disposition_date,
        "bond_amount": bond_amount,
        "bond_type": bond_type,
        "events": extracted_events,
        "estimated_voucher_amount": 1000.0 if "felony" in charge_description.lower() else 500.0,
        "ready_for_voucher": disposition_type != "PENDING" and has_appointment_order,
    }


@router.post("/parse-raw-text")
async def parse_raw_odyssey_text(
    data: ParseRawTextRequest,
    current_user: dict = Depends(get_current_user),
):
    """Parses raw text copied directly from Tyler Odyssey Portal (`Ctrl+A` -> `Ctrl+C`)."""
    if not data.raw_text or len(data.raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Pasted text is too short to parse.")

    parsed = _extract_case_info(data.raw_text)
    return {
        "success": True,
        "parsed_data": parsed,
        "message": f"Successfully parsed Odyssey record for Cause {parsed['case_number']}.",
    }


@router.post("/commit-raw-case")
async def commit_raw_odyssey_case(
    data: CommitRawCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Saves parsed Odyssey case into SQLite, creates client/events, and auto-generates voucher."""
    # 1. Find or create client
    res_client = await db.execute(select(Client).filter(Client.name == data.client_name))
    client = res_client.scalars().first()
    if not client:
        client = Client(name=data.client_name, notes="Created via Tyler Odyssey Raw Text Ingestion")
        db.add(client)
        await db.commit()
        await db.refresh(client)

    # 2. Find or create case
    res_case = await db.execute(select(Case).filter(Case.case_number == data.case_number))
    case = res_case.scalars().first()
    
    stage = "DISPOSED" if data.disposition_type != "PENDING" else "DISCOVERY"
    status = "DISPOSED" if data.disposition_type != "PENDING" else "APPOINTED"

    if not case:
        case = Case(
            client_id=client.id,
            case_number=data.case_number,
            court=data.court,
            judge=data.judge,
            charge_description=data.charge_description,
            status=status,
            stage=stage,
            is_cja=True,
            has_appointment_order=data.has_appointment_order,
            appointment_order_date=data.appointment_order_date,
            appointment_status=data.appointment_status,
            disposition_type=data.disposition_type,
            disposition_date=data.disposition_date,
            opened_date=data.file_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            closed_date=data.disposition_date,
            bond_amount=data.bond_amount,
            bond_type=data.bond_type,
            voucher_status="UNBILLED" if data.disposition_type != "PENDING" else "NONE",
            notes=data.notes or "Ingested via Tyler Odyssey Select-All & Paste parser.",
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
    else:
        # Update existing
        case.court = data.court
        case.judge = data.judge
        case.charge_description = data.charge_description or case.charge_description
        case.has_appointment_order = data.has_appointment_order
        case.appointment_order_date = data.appointment_order_date or case.appointment_order_date
        case.appointment_status = data.appointment_status
        case.disposition_type = data.disposition_type or case.disposition_type
        case.disposition_date = data.disposition_date or case.disposition_date
        if data.disposition_type != "PENDING":
            case.status = "DISPOSED"
            case.stage = "DISPOSED"
            case.closed_date = data.disposition_date
            if case.voucher_status in ("NONE", None):
                case.voucher_status = "UNBILLED"
        await db.commit()
        await db.refresh(case)

    # 3. Create Events
    for ev in data.events:
        try:
            ev_dt = datetime.strptime(ev.get("date", ""), "%m/%d/%Y").strftime("%Y-%m-%d")
        except Exception:
            ev_dt = ev.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        event_obj = Event(
            case_id=case.id,
            title=ev.get("title", "Court Event"),
            event_date=ev_dt,
            event_type="COURT_EVENT",
            description=ev.get("description", ""),
        )
        db.add(event_obj)
    
    await db.commit()

    # 4. Auto-create Voucher if requested
    created_voucher = None
    if data.auto_create_voucher and data.disposition_type != "PENDING":
        res_vch = await db.execute(select(Voucher).filter(Voucher.case_id == case.id))
        existing_vch = res_vch.scalars().first()
        if not existing_vch:
            v_amt = 1000.0 if "felony" in (case.charge_description or "").lower() else 500.0
            created_voucher = Voucher(
                case_id=case.id,
                voucher_number=f"VCH-{case.case_number}-{uuid.uuid4().hex[:8].upper()}",
                voucher_type="CJA-FELONY" if "felony" in (case.charge_description or "").lower() else "CJA-MISDEMEANOR",
                submission_method="ONLINE_PORTAL",
                status="DRAFT",
                has_appointment_order_verified=case.has_appointment_order,
                amount_requested=v_amt,
                disposition_date=case.disposition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                notes="Auto-created during Tyler Odyssey Raw Text Ingestion.",
            )
            db.add(created_voucher)
            case.voucher_status = "DRAFT"
            await db.commit()
            await db.refresh(created_voucher)

    return {
        "success": True,
        "case_id": case.id,
        "case_number": case.case_number,
        "client_name": client.name,
        "has_appointment_order": case.has_appointment_order,
        "disposition_type": case.disposition_type,
        "voucher_created": created_voucher is not None,
        "voucher_id": created_voucher.id if created_voucher else None,
        "message": f"Successfully ingested Cause {case.case_number} ({client.name}) and saved to database.",
    }
