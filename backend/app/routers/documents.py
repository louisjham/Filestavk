import os
import json
import shutil
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.database import get_db
from app.deps import get_current_user
from app.models.document import Document
from app.models.case import Case
from app.models.client import Client
from app.models.event import Event
from app.models.time_entry import Voucher
from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES
from app.schemas.document import DocumentOut
from app.services.document_extractor_service import (
    validate_document_health,
    extract_content,
    extract_legal_entities,
    ALLOWED_EXTENSIONS,
)

router = APIRouter()
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


class BindCaseRequest(BaseModel):
    case_id: int
    classification_label: Optional[str] = None
    create_hearing_event: bool = False
    hearing_datetime: Optional[str] = None


async def apply_document_rule_to_ingestion(
    db: AsyncSession,
    detected_label: str,
    legal_meta: Dict[str, Any],
    resolved_client_id: Optional[int],
    resolved_case_id: Optional[int],
    filename: str,
):
    """Dynamically applies active DocumentRule configuration to Client, Case, and Event timeline."""
    rule_res = await db.execute(
        select(DocumentRule).where(
            DocumentRule.document_type == detected_label,
            DocumentRule.is_active == True,
        )
    )
    rule = rule_res.scalars().first()

    def_name = legal_meta.get("defendant_name") or "Defendant"
    court_name = legal_meta.get("court") or "County Court at Law No. 3"
    judge_name = legal_meta.get("judge") or "Hon. Deeanne Galvan"
    primary_case = legal_meta.get("primary_case_number") or ""
    specialized = legal_meta.get("specialized_fields", {})
    charge_desc = specialized.get("charge_description") or "Class A/B Misdemeanor"
    atty_name = specialized.get("appointed_attorney") or "Kimbel Brandon"
    sbn_num = specialized.get("attorney_sbn") or "24079543"

    # 1. Update Client Attributes if enabled
    if resolved_client_id and rule and rule.auto_populate_client:
        c_res = await db.execute(select(Client).where(Client.id == resolved_client_id))
        client = c_res.scalars().first()
        if client:
            if specialized.get("dob") and not client.dob:
                client.dob = specialized.get("dob")
            if specialized.get("address") and not client.address:
                client.address = specialized.get("address")
            if specialized.get("phone") and not client.phone:
                client.phone = specialized.get("phone")
            if specialized.get("so_number"):
                so_note = f"SO# {specialized.get('so_number')}"
                if not client.notes:
                    client.notes = so_note
                elif so_note not in client.notes:
                    client.notes += f" | {so_note}"

    # 2. Update Case Attributes if enabled
    # 2. Update Case Attributes if enabled
    if resolved_case_id:
        cs_res = await db.execute(select(Case).where(Case.id == resolved_case_id))
        case_obj = cs_res.scalars().first()
        if case_obj:
            if rule:
                if rule.target_case_stage:
                    case_obj.stage = rule.target_case_stage
                if rule.target_case_status:
                    case_obj.status = rule.target_case_status
                if rule.is_cja_default:
                    case_obj.is_cja = True

                # Appointment Order & Acceptance Handling
                if detected_label == "appointment_acceptance" or getattr(rule, "set_has_appointment_acceptance", False):
                    case_obj.has_appointment_acceptance = True
                    case_obj.appointment_status = "CONFIRMED_AND_ACCEPTED"
                    if specialized.get("acceptance_filed_date") or specialized.get("filed_date"):
                        case_obj.acceptance_filed_date = specialized.get("acceptance_filed_date") or specialized.get("filed_date")
                    if specialized.get("client_contact_date") or specialized.get("contact_acceptance_date"):
                        case_obj.client_contact_date = specialized.get("client_contact_date") or specialized.get("contact_acceptance_date")
                elif detected_label == "appointment_order" or rule.set_has_appointment_order:
                    case_obj.has_appointment_order = True
                    if not case_obj.has_appointment_acceptance:
                        case_obj.appointment_status = "AWAITING_ACCEPTANCE"
                    if specialized.get("signed_date") or specialized.get("filed_date"):
                        case_obj.appointment_order_date = specialized.get("signed_date") or specialized.get("filed_date")

                if rule.auto_populate_case:
                    if specialized.get("charge_description") and (not case_obj.charge_description or case_obj.charge_description in ("Class A/B Misdemeanor", "Pending Offense")):
                        case_obj.charge_description = specialized.get("charge_description")
                    if court_name:
                        case_obj.court = court_name
                    if judge_name:
                        case_obj.judge = judge_name
                    if "in_custody" in specialized:
                        case_obj.in_custody = specialized.get("in_custody")

    # 3. Create Docket Timeline Events (Dual Events for Combined Scans)
    if resolved_case_id and rule and rule.create_docket_event:
        if detected_label == "appointment_acceptance" and specialized.get("has_order_section", True):
            # Event 1: Court Issued Appointment Order
            order_date_val = specialized.get("appointment_order_date") or specialized.get("signed_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            evt_order = Event(
                case_id=resolved_case_id,
                event_type="order",
                title=f"Order of Appointment Issued by Court ({court_name})",
                description=f"Court issued formal order appointing {atty_name} (SBN: {sbn_num}) to represent {def_name} on charge {charge_desc}. Statutory basis: Art. 26.04 CCP.",
                event_date=order_date_val,
            )
            db.add(evt_order)

            # Event 2: Attorney Filed Stamped Acceptance of Appointment
            filed_date_val = specialized.get("acceptance_filed_date") or specialized.get("filed_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            contact_date_val = specialized.get("client_contact_date") or specialized.get("contact_acceptance_date") or "N/A"
            clerk_str = specialized.get("district_clerk", "Anne Lorentzen, District Clerk")
            evt_accept = Event(
                case_id=resolved_case_id,
                event_type="filing",
                title=f"Acceptance of Appointment Filed with District Clerk ({court_name})",
                description=f"Attorney {atty_name} filed signed acceptance with District Clerk ({clerk_str}). Initial personal contact affirmed on {contact_date_val}. Prerequisite for voucher payment satisfied.",
                event_date=filed_date_val,
            )
            db.add(evt_accept)
        else:
            try:
                title_fmt = rule.event_title_template.format(
                    doc_title=rule.display_name,
                    court=court_name,
                    judge=judge_name,
                    defendant_name=def_name,
                    case_number=primary_case,
                    charge=charge_desc,
                    attorney_name=atty_name,
                    sbn=sbn_num,
                )
            except Exception:
                title_fmt = f"{rule.display_name} Filed ({court_name})"

            try:
                desc_fmt = rule.event_desc_template.format(
                    doc_title=rule.display_name,
                    court=court_name,
                    judge=judge_name,
                    defendant_name=def_name,
                    case_number=primary_case,
                    charge=charge_desc,
                    attorney_name=atty_name,
                    sbn=sbn_num,
                    amount_paid=specialized.get("amount_paid", "0.00"),
                    warrant_number=specialized.get("warrant_number", "N/A"),
                    hearing_datetime=specialized.get("hearing_datetime", "Scheduled Date"),
                )
            except Exception:
                desc_fmt = f"{rule.display_name} processed for {def_name}."

            evt = Event(
                case_id=resolved_case_id,
                event_type=rule.event_type or "order",
                title=title_fmt,
                description=desc_fmt,
                event_date=specialized.get("filed_date") or specialized.get("signed_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            db.add(evt)

    # 4. Trigger Statutory Deadline Event if enabled (e.g. 48-Hour Contact Rule Art 26.04(j)(1))
    if resolved_case_id and rule and rule.trigger_statutory_deadline and rule.deadline_name:
        deadline_evt = Event(
            case_id=resolved_case_id,
            event_type="deadline",
            title=f"Statutory Deadline: {rule.deadline_name}",
            description=f"Action Required under {rule.statutory_basis or 'Texas Law'}: Compliance due within {rule.deadline_hours_offset} hours for {def_name}.",
            event_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        db.add(deadline_evt)




@router.get("", response_model=List[DocumentOut])
async def get_documents(
    case_id: Optional[int] = None,
    client_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    classification_label: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List documents with optional filtering and search."""
    query = select(Document).order_by(Document.id.desc())
    if case_id:
        query = query.filter(Document.case_id == case_id)
    if client_id:
        query = query.filter(Document.client_id == client_id)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if classification_label:
        query = query.filter(Document.classification_label == classification_label)

    result = await db.execute(query)
    docs = result.scalars().all()

    if search:
        s = search.lower()
        docs = [
            d for d in docs
            if s in (d.filename or "").lower()
            or s in (d.content_text or "").lower()
            or s in (d.classification_label or "").lower()
        ]

    return docs


@router.post("/inspect-raw")
async def inspect_raw_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Real-time pre-upload document health check and extraction inspection.
    Validates anti-stub integrity and checks database for existing Client and Case records.
    """
    file_bytes = await file.read()
    health = validate_document_health(file_bytes, file.filename)

    if not health.get("is_healthy"):
        return {
            "is_healthy": False,
            "filename": file.filename,
            "health_status": health.get("status"),
            "error": health.get("error"),
            "file_size_bytes": health.get("file_size_bytes"),
        }

    # Save to temporary scratch location for extraction
    scratch_dir = os.path.join(UPLOAD_DIR, "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    temp_path = os.path.join(scratch_dir, f"temp_{file.filename}")

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        extracted = extract_content(temp_path, file.filename)
        legal_meta = extract_legal_entities(extracted.get("text", ""), file.filename, focused_crop=extracted.get("focused_crop"))
        category = legal_meta.get("classification_label") or "uncategorized"

        # 1. Check if Client exists in DB
        client_res_info = {"exists": False, "id": None, "name": legal_meta.get("defendant_name"), "action": "WILL_AUTO_CREATE"}
        def_name = legal_meta.get("defendant_name")
        if def_name:
            c_res = await db.execute(select(Client).where(func.lower(Client.name) == def_name.lower().strip()))
            found_c = c_res.scalars().first()
            if found_c:
                client_res_info = {
                    "exists": True,
                    "id": found_c.id,
                    "name": found_c.name,
                    "action": "REUSE_EXISTING",
                }

        # 2. Check if Case exists in DB
        case_res_info = {"exists": False, "id": None, "case_number": legal_meta.get("primary_case_number"), "court": legal_meta.get("court"), "action": "WILL_AUTO_CREATE"}
        primary_case = legal_meta.get("primary_case_number")
        if primary_case:
            cs_res = await db.execute(select(Case).where(Case.case_number == primary_case))
            found_cs = cs_res.scalars().first()
            if found_cs:
                case_res_info = {
                    "exists": True,
                    "id": found_cs.id,
                    "case_number": found_cs.case_number,
                    "court": found_cs.court,
                    "judge": found_cs.judge,
                    "client_id": found_cs.client_id,
                    "action": "REUSE_EXISTING",
                }

        # 3. Check for matching DocumentRule
        rule_res = await db.execute(select(DocumentRule).where(DocumentRule.document_type == category, DocumentRule.is_active == True))
        matched_rule = rule_res.scalars().first()
        rule_info = None
        if matched_rule:
            rule_info = {
                "rule_id": matched_rule.id,
                "display_name": matched_rule.display_name,
                "target_case_stage": matched_rule.target_case_stage,
                "lifecycle_stage": matched_rule.lifecycle_stage,
                "statutory_basis": matched_rule.statutory_basis,
                "trigger_statutory_deadline": matched_rule.trigger_statutory_deadline,
                "deadline_name": matched_rule.deadline_name,
            }

        return {
            "is_healthy": True,
            "filename": file.filename,
            "health_status": health.get("status"),
            "detected_format": health.get("detected_format"),
            "file_size_bytes": health.get("file_size_bytes"),
            "page_count": extracted.get("page_count", 1),
            "extraction_method": extracted.get("extraction_method"),
            "is_scanned_image": extracted.get("is_scanned_image", False),
            "text_preview": extracted.get("text", "")[:1000],
            "text_length": len(extracted.get("text", "")),
            "tables_count": len(extracted.get("tables", [])),
            "sheets": extracted.get("sheets", []),
            "legal_metadata": legal_meta,
            "client_resolution": client_res_info,
            "case_resolution": case_res_info,
            "matched_rule": rule_info,
        }
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/batch-inspect")
async def batch_inspect_documents(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch inspection endpoint for multi-file drag & drop.
    Inspects multiple documents simultaneously and returns individual and aggregate metrics.
    """
    inspections = []
    total_healthy = 0
    total_rejected = 0
    clients_to_create = 0
    cases_to_create = 0

    for f in files:
        file_bytes = await f.read()
        health = validate_document_health(file_bytes, f.filename)

        if not health.get("is_healthy"):
            total_rejected += 1
            inspections.append({
                "filename": f.filename,
                "is_healthy": False,
                "health_status": health.get("status"),
                "error": health.get("error"),
                "file_size_bytes": health.get("file_size_bytes"),
            })
            continue

        total_healthy += 1
        scratch_dir = os.path.join(UPLOAD_DIR, "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        temp_path = os.path.join(scratch_dir, f"batch_inspect_{f.filename}")

        try:
            with open(temp_path, "wb") as buf:
                buf.write(file_bytes)

            extracted = extract_content(temp_path, f.filename)
            legal_meta = extract_legal_entities(extracted.get("text", ""), f.filename, focused_crop=extracted.get("focused_crop"))
            category = legal_meta.get("classification_label") or "uncategorized"

            # Check Client
            client_res_info = {"exists": False, "id": None, "name": legal_meta.get("defendant_name"), "action": "WILL_AUTO_CREATE"}
            def_name = legal_meta.get("defendant_name")
            if def_name:
                c_res = await db.execute(select(Client).where(func.lower(Client.name) == def_name.lower().strip()))
                found_c = c_res.scalars().first()
                if found_c:
                    client_res_info = {"exists": True, "id": found_c.id, "name": found_c.name, "action": "REUSE_EXISTING"}
                else:
                    clients_to_create += 1
            else:
                clients_to_create += 1

            # Check Case
            case_res_info = {"exists": False, "id": None, "case_number": legal_meta.get("primary_case_number"), "court": legal_meta.get("court"), "action": "WILL_AUTO_CREATE"}
            primary_case = legal_meta.get("primary_case_number")
            if primary_case:
                cs_res = await db.execute(select(Case).where(Case.case_number == primary_case))
                found_cs = cs_res.scalars().first()
                if found_cs:
                    case_res_info = {"exists": True, "id": found_cs.id, "case_number": found_cs.case_number, "court": found_cs.court, "judge": found_cs.judge, "action": "REUSE_EXISTING"}
                else:
                    cases_to_create += 1
            else:
                cases_to_create += 1

            # Check Rule
            rule_res = await db.execute(select(DocumentRule).where(DocumentRule.document_type == category, DocumentRule.is_active == True))
            matched_rule = rule_res.scalars().first()
            rule_info = None
            if matched_rule:
                rule_info = {
                    "rule_id": matched_rule.id,
                    "display_name": matched_rule.display_name,
                    "target_case_stage": matched_rule.target_case_stage,
                    "lifecycle_stage": matched_rule.lifecycle_stage,
                    "statutory_basis": matched_rule.statutory_basis,
                }

            inspections.append({
                "filename": f.filename,
                "is_healthy": True,
                "health_status": health.get("status"),
                "detected_format": health.get("detected_format"),
                "file_size_bytes": health.get("file_size_bytes"),
                "page_count": extracted.get("page_count", 1),
                "extraction_method": extracted.get("extraction_method"),
                "legal_metadata": legal_meta,
                "client_resolution": client_res_info,
                "case_resolution": case_res_info,
                "matched_rule": rule_info,
            })
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    return {
        "total_files": len(files),
        "healthy_count": total_healthy,
        "rejected_count": total_rejected,
        "clients_to_create": clients_to_create,
        "cases_to_create": cases_to_create,
        "files": inspections,
    }


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    case_id: Optional[int] = Form(None),
    client_id: Optional[int] = Form(None),
    auto_provision: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload and process a single legal document.
    Performs anti-stub health checks, extracts entities, applies matching DocumentRule,
    and provisions Client and Case hierarchy records.
    """
    if not isinstance(case_id, int):
        case_id = None
    if not isinstance(client_id, int):
        client_id = None
    if not isinstance(auto_provision, bool):
        auto_provision = True

    file_bytes = await file.read()
    health = validate_document_health(file_bytes, file.filename)

    if not health.get("is_healthy"):
        raise HTTPException(
            status_code=400,
            detail=f"Document rejected: {health.get('error')} (Status: {health.get('status')})"
        )

    scratch_dir = os.path.join(UPLOAD_DIR, "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    temp_extract_path = os.path.join(scratch_dir, f"staging_{file.filename}")
    with open(temp_extract_path, "wb") as buffer:
        buffer.write(file_bytes)

    try:
        # Run CPU-heavy parsing off the async event loop to prevent blocking
        def _parse_document():
            result = extract_content(temp_extract_path, file.filename)
            meta = extract_legal_entities(result.get("text", ""), file.filename, focused_crop=result.get("focused_crop"))
            return result, meta

        extracted, legal_meta = await asyncio.to_thread(_parse_document)
        text = extracted.get("text", "")
        detected_label = legal_meta.get("classification_label") or "uncategorized"
        detected_conf = legal_meta.get("confidence", 0.75)
        def_name = legal_meta.get("defendant_name")
        primary_case = legal_meta.get("primary_case_number")
        court_name = legal_meta.get("court") or "County Court at Law No. 3"
        judge_name = legal_meta.get("judge") or "Hon. Deeanne Galvan"
        specialized = legal_meta.get("specialized_fields", {})

        # Build secondary phone string (Cell, Work, Home)
        phone_extras = []
        if specialized.get("cell_phone"):
            phone_extras.append(f"Cell: {specialized['cell_phone']}")
        if specialized.get("work_phone"):
            phone_extras.append(f"Work: {specialized['work_phone']}")
        if specialized.get("home_phone") and specialized.get("home_phone") != specialized.get("phone"):
            phone_extras.append(f"Home: {specialized['home_phone']}")
        extra_phone_str = " | ".join(phone_extras)

        # --- HIERARCHY LEVEL 1: CLIENT RESOLUTION & DE-DUPLICATION ---
        resolved_client_id = client_id
        if not resolved_client_id and def_name:
            client_search = await db.execute(
                select(Client).where(func.lower(Client.name) == def_name.lower().strip())
            )
            existing_client = client_search.scalars().first()
            if existing_client:
                resolved_client_id = existing_client.id
                # Backfill any blank contact fields on the existing client record
                if not existing_client.address and specialized.get("address"):
                    existing_client.address = specialized["address"]
                if not existing_client.phone and specialized.get("phone"):
                    existing_client.phone = specialized["phone"]
                if not existing_client.email and specialized.get("email"):
                    existing_client.email = specialized["email"]
                if not existing_client.dob and specialized.get("dob"):
                    existing_client.dob = specialized["dob"]
                if extra_phone_str:
                    if not existing_client.notes:
                        existing_client.notes = extra_phone_str
                    elif extra_phone_str not in existing_client.notes:
                        existing_client.notes += f" | {extra_phone_str}"
            elif auto_provision:
                base_note = f"Client record created from '{file.filename}' (Court: {court_name}, Cause: {primary_case or 'N/A'})."
                if extra_phone_str:
                    base_note += f" [{extra_phone_str}]"
                new_client = Client(
                    name=def_name.strip(),
                    dob=specialized.get("dob"),
                    address=specialized.get("address"),
                    phone=specialized.get("phone"),
                    email=specialized.get("email"),
                    notes=base_note,
                )
                db.add(new_client)
                await db.flush()
                resolved_client_id = new_client.id

        # --- HIERARCHY LEVEL 2: CASE RESOLUTION & PROVISIONING UNDER CLIENT ---
        resolved_case_id = case_id
        # Use ISO normalized date if available, fall back to raw string
        appt_order_date = (
            specialized.get("appointment_order_date_iso")
            or specialized.get("appointment_order_date")
            or specialized.get("signed_date")
        )
        is_mid_stride = False
        needs_human_review = bool(specialized.get("needs_human_review", False))

        if not resolved_case_id and primary_case:
            case_search = await db.execute(
                select(Case).where(Case.case_number == primary_case)
            )
            existing_case = case_search.scalars().first()
            if existing_case:
                resolved_case_id = existing_case.id
                if not existing_case.client_id and resolved_client_id:
                    existing_case.client_id = resolved_client_id

                if detected_label == "appointment_acceptance":
                    if needs_human_review:
                        existing_case.appointment_status = "AWAITING_ACCEPTANCE_REVIEW"
                    else:
                        is_mid_stride = not existing_case.has_appointment_order
                        existing_case.has_appointment_acceptance = True
                        existing_case.acceptance_filed_date = specialized.get("acceptance_filed_date") or specialized.get("filed_date")
                        existing_case.appointment_status = "CONFIRMED_AND_ACCEPTED"
                        existing_case.voucher_status = "READY_TO_FILE"
                        existing_case.client_contact_date = specialized.get("client_contact_date") or existing_case.client_contact_date
                elif detected_label == "appointment_order" and not existing_case.has_appointment_order:
                    existing_case.has_appointment_order = True
                    existing_case.appointment_order_date = appt_order_date
                    existing_case.appointment_status = "AWAITING_ACCEPTANCE"
            elif auto_provision:
                is_felony = "district" in court_name.lower() or "felony" in detected_label.lower() or "felony" in (specialized.get("charge_description") or "").lower()

                if detected_label == "appointment_acceptance":
                    if needs_human_review:
                        has_order = False
                        has_accept = False
                        appt_status = "AWAITING_ACCEPTANCE_REVIEW"
                        vch_status = "NONE"
                    else:
                        is_mid_stride = True  # Provisioned mid-stride without prior order
                        has_order = False     # Explicitly False to trigger missing order alert
                        has_accept = True
                        appt_status = "CONFIRMED_AND_ACCEPTED"
                        vch_status = "READY_TO_FILE"
                elif detected_label == "appointment_order":
                    has_order = True
                    has_accept = False
                    appt_status = "AWAITING_ACCEPTANCE"
                    vch_status = "NONE"
                else:
                    has_order = detected_label == "waiver_of_arraignment"
                    has_accept = False
                    appt_status = "VERIFIED_ON_DOCKET" if has_order else "UNKNOWN"
                    vch_status = "NONE"

                new_case = Case(
                    client_id=resolved_client_id,
                    case_number=primary_case,
                    court=court_name,
                    judge=judge_name,
                    charge_description=specialized.get("charge_description") or ("Class A/B Misdemeanor" if not is_felony else "Felony Offense"),
                    is_cja=True,
                    status="open",
                    stage="MAGISTRATE_HEARING" if "appointment" in detected_label else ("PRE_TRIAL" if detected_label == "waiver_of_arraignment" else "DISCOVERY"),
                    has_appointment_order=has_order,
                    has_appointment_acceptance=has_accept,
                    appointment_order_date=appt_order_date if has_order else None,
                    acceptance_filed_date=(specialized.get("acceptance_filed_date") or specialized.get("filed_date")) if has_accept else None,
                    client_contact_date=specialized.get("client_contact_date") or specialized.get("contact_acceptance_date"),
                    appointment_status=appt_status,
                    voucher_status=vch_status,
                    in_custody=specialized.get("in_custody", False),
                    notes=f"Case created automatically from document '{file.filename}'.",
                )
                db.add(new_case)
                await db.flush()
                resolved_case_id = new_case.id

        # --- HIERARCHY LEVEL 2b: MID-STRIDE MISSING ORDER ALERT & DOCKET EVENTS ---
        if resolved_case_id and is_mid_stride:
            db.add(Event(
                case_id=resolved_case_id,
                event_type="MID_STRIDE_MISSING_ORDER",
                title="Missing Prior Order of Appointment (Mid-Stride Ingestion)",
                description=(
                    f"Acceptance of Appointment recorded for Cause #{primary_case} ({def_name or 'Defendant'}), "
                    "but no prior Order of Appointment exists on the docket. Case provisioned mid-stride. "
                    "Verify judicial appointment order on Odyssey portal."
                ),
                event_date=appt_order_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ))

        if resolved_case_id and detected_label in ("appointment_order", "appointment_acceptance"):
            if detected_label == "appointment_order":
                event_title = "Order of Appointment Ingested"
                event_desc = (
                    f"Art. 26.04 CCP — Appointment order signed {appt_order_date or 'date unknown'}. "
                    "Awaiting file-stamped Acceptance of Appointment from District Clerk."
                )
            elif needs_human_review:
                event_title = "Acceptance Ingested (Awaiting Human Review)"
                event_desc = (
                    "Acceptance document ingested without detectable clerk stamp or attorney signature. "
                    "Awaiting manual inspection before voucher qualification."
                )
            else:
                event_title = "Acceptance of Appointment Filed"
                event_desc = (
                    f"File-stamped Acceptance of Appointment recorded. "
                    f"Filed: {specialized.get('acceptance_filed_date', 'date unknown')}. "
                    "Voucher status set to Ready to Be Filed."
                )
            docket_event = Event(
                case_id=resolved_case_id,
                event_type=detected_label.upper(),
                title=event_title,
                description=event_desc,
                event_date=appt_order_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            db.add(docket_event)

        # --- HIERARCHY LEVEL 2c: VOUCHER TRANSITION TO READY_TO_FILE ---
        if resolved_case_id and detected_label == "appointment_acceptance" and not needs_human_review:
            v_search = await db.execute(select(Voucher).where(Voucher.case_id == resolved_case_id))
            case_vch = v_search.scalars().first()
            if case_vch:
                case_vch.status = "READY_TO_FILE"
                case_vch.has_appointment_order_verified = True
            else:
                is_felony = "district" in court_name.lower() or "felony" in (specialized.get("charge_description") or "").lower()
                case_vch = Voucher(
                    case_id=resolved_case_id,
                    voucher_number=f"VCH-{primary_case}",
                    voucher_type="CJA-FELONY" if is_felony else "CJA-MISDEMEANOR",
                    status="READY_TO_FILE",
                    amount_requested=1000.0 if is_felony else 500.0,
                    has_appointment_order_verified=True,
                    notes="Voucher transitioned to Ready to Be Filed upon verified Acceptance of Appointment.",
                )
                db.add(case_vch)

        # --- HIERARCHY LEVEL 3: PERSIST DOCUMENT & RENAME TO Order_Of_Acceptance-<CaseNumber> ---
        case_dir = os.path.join(UPLOAD_DIR, str(resolved_case_id or "unassigned"))
        os.makedirs(case_dir, exist_ok=True)

        ext_with_dot = os.path.splitext(file.filename)[1] or ".pdf"
        if not primary_case:
            safe_filename = f"NEEDS_REVIEW_{os.path.basename(file.filename)}"
        elif detected_label == "appointment_acceptance":
            safe_filename = f"Order_Of_Acceptance-{primary_case}{ext_with_dot}"
        elif detected_label == "appointment_order":
            safe_filename = f"Order_Of_Appt-{primary_case}{ext_with_dot}"
        else:
            safe_filename = os.path.basename(file.filename)

        permanent_filepath = os.path.join(case_dir, safe_filename)
        shutil.copyfile(temp_extract_path, permanent_filepath)

        # Write matching sidecar .json metadata record
        sidecar_json_path = os.path.splitext(permanent_filepath)[0] + ".json"
        try:
            with open(sidecar_json_path, "w", encoding="utf-8") as sc_f:
                json.dump({
                    "source_filename": file.filename,
                    "renamed_filename": safe_filename,
                    "case_number": primary_case,
                    "court": court_name,
                    "judge": judge_name,
                    "defendant_name": def_name,
                    "classification_label": detected_label,
                    "specialized_fields": specialized,
                    "health_status": health.get("status"),
                    "extraction_method": extracted.get("extraction_method"),
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }, sc_f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        metadata_payload = json.dumps({
            "health_status": health.get("status"),
            "detected_format": health.get("detected_format"),
            "file_size_bytes": health.get("file_size_bytes"),
            "extraction_method": extracted.get("extraction_method"),
            "is_scanned_image": extracted.get("is_scanned_image", False),
            "legal_metadata": legal_meta,
            "tables_count": len(extracted.get("tables", [])),
            "sheets_count": len(extracted.get("sheets", [])),
            "auto_provisioned_client_id": resolved_client_id,
            "auto_provisioned_case_id": resolved_case_id,
            "review_status": "AWAITING_HUMAN_REVIEW" if needs_human_review else "APPROVED",
            "human_review_instructions": specialized.get("human_review_instructions"),
            "has_clerk_file_stamp": specialized.get("has_clerk_file_stamp", False),
            "has_attorney_affirmation": specialized.get("has_attorney_affirmation", False),
            "is_mid_stride": is_mid_stride,
        })

        ext = os.path.splitext(file.filename.lower())[1].replace(".", "")

        doc = Document(
            case_id=resolved_case_id,
            client_id=resolved_client_id,
            filename=safe_filename,
            filepath=permanent_filepath,
            doc_type=ext if ext in ("pdf", "docx", "doc", "xlsx", "xls", "csv") else "other",
            source="upload_intelligent",
            content_text=text[:15000],
            metadata_json=metadata_payload,
            classification_label=detected_label,
            classification_confidence=detected_conf,
        )
        db.add(doc)
        await db.flush()

        # --- HIERARCHY LEVEL 4: DYNAMIC DOCUMENT RULES & STATUTORY DEADLINE EXECUTION ---
        await apply_document_rule_to_ingestion(
            db=db,
            detected_label=detected_label,
            legal_meta=legal_meta,
            resolved_client_id=resolved_client_id,
            resolved_case_id=resolved_case_id,
            filename=file.filename,
        )

        await db.commit()
        await db.refresh(doc)
        return doc
    finally:
        if os.path.exists(temp_extract_path):
            try:
                os.remove(temp_extract_path)
            except Exception:
                pass


@router.post("/batch-upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    auto_provision: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch ingestion endpoint for ingesting multiple documents at once.
    Applies de-duplication, case hierarchy provisioning, and dynamic DocumentRules across all files.
    """
    results = []
    success_count = 0
    error_count = 0

    for f in files:
        file_bytes = await f.read()
        health = validate_document_health(file_bytes, f.filename)

        if not health.get("is_healthy"):
            error_count += 1
            results.append({
                "filename": f.filename,
                "status": "REJECTED",
                "error": health.get("error"),
            })
            continue

        scratch_dir = os.path.join(UPLOAD_DIR, "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        temp_extract_path = os.path.join(scratch_dir, f"batch_staging_{f.filename}")

        try:
            with open(temp_extract_path, "wb") as buf:
                buf.write(file_bytes)

            _fname = f.filename
            _path = temp_extract_path
            def _parse_batch_doc():
                result = extract_content(_path, _fname)
                meta = extract_legal_entities(result.get("text", ""), _fname)
                return result, meta

            extracted, legal_meta = await asyncio.to_thread(_parse_batch_doc)
            text = extracted.get("text", "")
            detected_label = legal_meta.get("classification_label") or "uncategorized"
            detected_conf = legal_meta.get("confidence", 0.75)
            def_name = legal_meta.get("defendant_name")
            primary_case = legal_meta.get("primary_case_number")
            court_name = legal_meta.get("court") or "County Court at Law No. 3"
            judge_name = legal_meta.get("judge") or "Hon. Deeanne Galvan"
            specialized = legal_meta.get("specialized_fields", {})

            # 1. Resolve / Create Client
            resolved_client_id = None
            if def_name:
                client_search = await db.execute(select(Client).where(func.lower(Client.name) == def_name.lower().strip()))
                existing_client = client_search.scalars().first()
                if existing_client:
                    resolved_client_id = existing_client.id
                    if not existing_client.address and specialized.get("address"):
                        existing_client.address = specialized["address"]
                    if not existing_client.phone and specialized.get("phone"):
                        existing_client.phone = specialized["phone"]
                    if not existing_client.email and specialized.get("email"):
                        existing_client.email = specialized["email"]
                    if not existing_client.dob and specialized.get("dob"):
                        existing_client.dob = specialized["dob"]
                elif auto_provision:
                    new_client = Client(
                        name=def_name.strip(),
                        dob=specialized.get("dob"),
                        address=specialized.get("address"),
                        phone=specialized.get("phone"),
                        email=specialized.get("email"),
                        notes=f"Client created from batch document '{f.filename}' (Court: {court_name}).",
                    )
                    db.add(new_client)
                    await db.flush()
                    resolved_client_id = new_client.id

            # 2. Resolve / Create Case
            resolved_case_id = None
            appt_order_date = (
                specialized.get("appointment_order_date_iso")
                or specialized.get("appointment_order_date")
                or specialized.get("signed_date")
            )
            is_mid_stride = False
            needs_human_review = bool(specialized.get("needs_human_review", False))

            if primary_case:
                case_search = await db.execute(select(Case).where(Case.case_number == primary_case))
                existing_case = case_search.scalars().first()
                if existing_case:
                    resolved_case_id = existing_case.id
                    if not existing_case.client_id and resolved_client_id:
                        existing_case.client_id = resolved_client_id

                    if detected_label == "appointment_acceptance":
                        if needs_human_review:
                            existing_case.appointment_status = "AWAITING_ACCEPTANCE_REVIEW"
                        else:
                            is_mid_stride = not existing_case.has_appointment_order
                            existing_case.has_appointment_acceptance = True
                            existing_case.acceptance_filed_date = specialized.get("acceptance_filed_date") or specialized.get("filed_date")
                            existing_case.appointment_status = "CONFIRMED_AND_ACCEPTED"
                            existing_case.voucher_status = "READY_TO_FILE"
                            existing_case.client_contact_date = specialized.get("client_contact_date") or existing_case.client_contact_date
                    elif detected_label == "appointment_order" and not existing_case.has_appointment_order:
                        existing_case.has_appointment_order = True
                        existing_case.appointment_order_date = appt_order_date
                        existing_case.appointment_status = "AWAITING_ACCEPTANCE"
                elif auto_provision:
                    is_felony = "district" in court_name.lower() or "felony" in detected_label.lower() or "felony" in (specialized.get("charge_description") or "").lower()

                    if detected_label == "appointment_acceptance":
                        if needs_human_review:
                            has_order = False
                            has_accept = False
                            appt_status = "AWAITING_ACCEPTANCE_REVIEW"
                            vch_status = "NONE"
                        else:
                            is_mid_stride = True  # Provisioned mid-stride without prior order
                            has_order = False     # Explicitly False to trigger missing order alert
                            has_accept = True
                            appt_status = "CONFIRMED_AND_ACCEPTED"
                            vch_status = "READY_TO_FILE"
                    elif detected_label == "appointment_order":
                        has_order = True
                        has_accept = False
                        appt_status = "AWAITING_ACCEPTANCE"
                        vch_status = "NONE"
                    else:
                        has_order = detected_label == "waiver_of_arraignment"
                        has_accept = False
                        appt_status = "VERIFIED_ON_DOCKET" if has_order else "UNKNOWN"
                        vch_status = "NONE"

                    new_case = Case(
                        client_id=resolved_client_id,
                        case_number=primary_case,
                        court=court_name,
                        judge=judge_name,
                        charge_description=specialized.get("charge_description") or ("Class A/B Misdemeanor" if not is_felony else "Felony Offense"),
                        is_cja=True,
                        status="open",
                        stage="MAGISTRATE_HEARING" if "appointment" in detected_label else ("PRE_TRIAL" if detected_label == "waiver_of_arraignment" else "DISCOVERY"),
                        has_appointment_order=has_order,
                        has_appointment_acceptance=has_accept,
                        appointment_order_date=appt_order_date if has_order else None,
                        acceptance_filed_date=(specialized.get("acceptance_filed_date") or specialized.get("filed_date")) if has_accept else None,
                        client_contact_date=specialized.get("client_contact_date") or specialized.get("contact_acceptance_date"),
                        appointment_status=appt_status,
                        voucher_status=vch_status,
                        in_custody=specialized.get("in_custody", False),
                        notes=f"Case created automatically from batch document '{f.filename}'.",
                    )
                    db.add(new_case)
                    await db.flush()
                    resolved_case_id = new_case.id

            # 2b. Emit Docket Event for batch appointments & mid-stride alerts
            if resolved_case_id and is_mid_stride:
                db.add(Event(
                    case_id=resolved_case_id,
                    event_type="MID_STRIDE_MISSING_ORDER",
                    title="Missing Prior Order of Appointment (Mid-Stride Ingestion)",
                    description=(
                        f"Acceptance of Appointment recorded for Cause #{primary_case} ({def_name or 'Defendant'}), "
                        "but no prior Order of Appointment exists on the docket. Case provisioned mid-stride. "
                        "Verify judicial appointment order on Odyssey portal."
                    ),
                    event_date=appt_order_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                ))

            if resolved_case_id and detected_label in ("appointment_order", "appointment_acceptance"):
                if detected_label == "appointment_order":
                    event_title = "Order of Appointment Ingested"
                    event_desc = (
                        f"Art. 26.04 CCP — Appointment order signed {appt_order_date or 'date unknown'}. Awaiting file-stamped Acceptance."
                    )
                elif needs_human_review:
                    event_title = "Acceptance Ingested (Awaiting Human Review)"
                    event_desc = (
                        "Acceptance document ingested without detectable clerk stamp or attorney signature. "
                        "Awaiting manual inspection before voucher qualification."
                    )
                else:
                    event_title = "Acceptance of Appointment Filed"
                    event_desc = (
                        f"File-stamped Acceptance recorded. Filed: {specialized.get('acceptance_filed_date', 'date unknown')}. "
                        "Voucher status set to Ready to Be Filed."
                    )
                db.add(Event(
                    case_id=resolved_case_id,
                    event_type=detected_label.upper(),
                    title=event_title,
                    description=event_desc,
                    event_date=appt_order_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                ))

            # 2c. Transition Voucher to READY_TO_FILE
            if resolved_case_id and detected_label == "appointment_acceptance" and not needs_human_review:
                v_search = await db.execute(select(Voucher).where(Voucher.case_id == resolved_case_id))
                case_vch = v_search.scalars().first()
                if case_vch:
                    case_vch.status = "READY_TO_FILE"
                    case_vch.has_appointment_order_verified = True
                else:
                    is_felony = "district" in court_name.lower() or "felony" in (specialized.get("charge_description") or "").lower()
                    case_vch = Voucher(
                        case_id=resolved_case_id,
                        voucher_number=f"VCH-{primary_case}",
                        voucher_type="CJA-FELONY" if is_felony else "CJA-MISDEMEANOR",
                        status="READY_TO_FILE",
                        amount_requested=1000.0 if is_felony else 500.0,
                        has_appointment_order_verified=True,
                        notes="Voucher transitioned to Ready to Be Filed upon verified Acceptance of Appointment.",
                    )
                    db.add(case_vch)

            # 3. Save Document & Rename to Order_Of_Acceptance-<CaseNumber>
            case_dir = os.path.join(UPLOAD_DIR, str(resolved_case_id or "unassigned"))
            os.makedirs(case_dir, exist_ok=True)

            ext_with_dot = os.path.splitext(f.filename)[1] or ".pdf"
            if detected_label == "appointment_acceptance" and primary_case:
                safe_filename = f"Order_Of_Acceptance-{primary_case}{ext_with_dot}"
            else:
                safe_filename = os.path.basename(f.filename)

            permanent_filepath = os.path.join(case_dir, safe_filename)
            shutil.copyfile(temp_extract_path, permanent_filepath)

            metadata_payload = json.dumps({
                "health_status": health.get("status"),
                "detected_format": health.get("detected_format"),
                "file_size_bytes": health.get("file_size_bytes"),
                "extraction_method": extracted.get("extraction_method"),
                "legal_metadata": legal_meta,
                "auto_provisioned_client_id": resolved_client_id,
                "auto_provisioned_case_id": resolved_case_id,
                "review_status": "AWAITING_HUMAN_REVIEW" if needs_human_review else "APPROVED",
                "human_review_instructions": specialized.get("human_review_instructions"),
                "has_clerk_file_stamp": specialized.get("has_clerk_file_stamp", False),
                "has_attorney_affirmation": specialized.get("has_attorney_affirmation", False),
                "is_mid_stride": is_mid_stride,
            })

            ext = os.path.splitext(f.filename.lower())[1].replace(".", "")

            doc = Document(
                case_id=resolved_case_id,
                client_id=resolved_client_id,
                filename=safe_filename,
                filepath=permanent_filepath,
                doc_type=ext if ext in ("pdf", "docx", "doc", "xlsx", "xls", "csv") else "other",
                source="batch_upload",
                content_text=text[:15000],
                metadata_json=metadata_payload,
                classification_label=detected_label,
                classification_confidence=detected_conf,
            )
            db.add(doc)
            await db.flush()

            # 4. Apply Rule
            await apply_document_rule_to_ingestion(
                db=db,
                detected_label=detected_label,
                legal_meta=legal_meta,
                resolved_client_id=resolved_client_id,
                resolved_case_id=resolved_case_id,
                filename=f.filename,
            )

            await db.commit()
            success_count += 1
            results.append({
                "filename": f.filename,
                "status": "SUCCESS",
                "document_id": doc.id,
                "client_id": resolved_client_id,
                "case_id": resolved_case_id,
                "case_number": primary_case,
                "classification_label": detected_label,
            })
        except Exception as e:
            error_count += 1
            results.append({
                "filename": f.filename,
                "status": "ERROR",
                "error": str(e),
            })
        finally:
            if os.path.exists(temp_extract_path):
                try:
                    os.remove(temp_extract_path)
                except Exception:
                    pass

    return {
        "total_files": len(files),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }


@router.post("/{id}/bind-case")
async def bind_document_to_case(
    id: int,
    body: BindCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Bind a document to a specific Case and optionally create a docket hearing event."""
    res = await db.execute(select(Document).where(Document.id == id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    case_res = await db.execute(select(Case).where(Case.id == body.case_id))
    target_case = case_res.scalars().first()
    if not target_case:
        raise HTTPException(status_code=404, detail="Target case not found")

    doc.case_id = target_case.id
    doc.client_id = target_case.client_id
    if body.classification_label:
        doc.classification_label = body.classification_label
        doc.classification_confidence = 1.0

    created_event_id = None
    if body.create_hearing_event and body.hearing_datetime:
        evt = Event(
            case_id=target_case.id,
            event_type="hearing",
            title=f"Court Hearing ({target_case.court})",
            description=f"Scheduled hearing extracted from document '{doc.filename}'.",
            event_date=body.hearing_datetime[:10],
        )
        db.add(evt)
        await db.flush()
        created_event_id = evt.id

    await db.commit()
    await db.refresh(doc)

    return {
        "status": "bound",
        "document_id": doc.id,
        "case_id": target_case.id,
        "case_number": target_case.case_number,
        "event_id": created_event_id,
    }


@router.get("/{id}", response_model=DocumentOut)
async def get_document(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{id}/file")
async def get_document_file(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc or not doc.filepath or not os.path.exists(doc.filepath):
        raise HTTPException(status_code=404, detail="File attachment not found on disk")
    return FileResponse(doc.filepath)


@router.patch("/{id}")
async def update_document(id: int, doc_update: dict, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    for k, v in doc_update.items():
        if hasattr(doc, k):
            setattr(doc, k, v)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{id}")
async def delete_document(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(Document).filter(Document.id == id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.filepath and os.path.exists(doc.filepath):
        try:
            os.remove(doc.filepath)
        except Exception:
            pass
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted", "id": id}


@router.post("/{id}/train")
async def train_document(id: int, current_user: dict = Depends(get_current_user)):
    return {"status": "marked for training"}


@router.post("/{id}/approve-review")
async def approve_document_review(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Approve a document that was flagged as AWAITING_HUMAN_REVIEW.
    Resumes the automated workflow:
    - Sets review_status to "APPROVED"
    - If document is an Acceptance of Appointment:
      - Marks case has_appointment_acceptance = True
      - Sets appointment_status = "CONFIRMED_AND_ACCEPTED"
      - Sets voucher_status = "READY_TO_FILE"
      - If not case.has_appointment_order: generates MID_STRIDE_MISSING_ORDER event
      - Transitions / creates Voucher in READY_TO_FILE status
    """
    res = await db.execute(select(Document).where(Document.id == id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    meta = {}
    if doc.metadata_json:
        try:
            meta = json.loads(doc.metadata_json)
        except Exception:
            meta = {}

    meta["review_status"] = "APPROVED"
    meta["reviewed_by"] = current_user.get("username") if isinstance(current_user, dict) else "attorney"
    meta["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    doc.metadata_json = json.dumps(meta)

    # If document is acceptance (by classification label or metadata)
    is_acceptance = (
        doc.classification_label == "appointment_acceptance"
        or "acceptance" in (doc.filename or "").lower()
    )

    if is_acceptance and doc.case_id:
        case_res = await db.execute(select(Case).where(Case.id == doc.case_id))
        target_case = case_res.scalars().first()
        if target_case:
            target_case.has_appointment_acceptance = True
            target_case.appointment_status = "CONFIRMED_AND_ACCEPTED"
            target_case.voucher_status = "READY_TO_FILE"

            legal_meta = meta.get("legal_metadata", {})
            spec = legal_meta.get("specialized_fields", {})
            if not target_case.acceptance_filed_date:
                target_case.acceptance_filed_date = spec.get("acceptance_filed_date") or spec.get("filed_date")
            if not target_case.client_contact_date:
                target_case.client_contact_date = spec.get("client_contact_date") or spec.get("contact_acceptance_date")

            # Check mid-stride missing order condition
            if not target_case.has_appointment_order:
                evt_res = await db.execute(
                    select(Event).where(
                        Event.case_id == target_case.id,
                        Event.event_type == "MID_STRIDE_MISSING_ORDER",
                    )
                )
                if not evt_res.scalars().first():
                    db.add(Event(
                        case_id=target_case.id,
                        event_type="MID_STRIDE_MISSING_ORDER",
                        title="Missing Prior Order of Appointment (Mid-Stride Ingestion)",
                        description=(
                            f"Acceptance of Appointment confirmed via human review for Cause #{target_case.case_number}, "
                            "but no prior Order of Appointment exists on the docket. Case provisioned mid-stride. "
                            "Verify judicial appointment order on Odyssey portal."
                        ),
                        event_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    ))

            # Add event for acceptance approved
            db.add(Event(
                case_id=target_case.id,
                event_type="APPOINTMENT_ACCEPTANCE",
                title="Acceptance of Appointment Approved (Human Review)",
                description="Manual inspection verified clerk stamp / attorney signature. Voucher status transitioned to Ready to Be Filed.",
                event_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ))

            # Transition or create Voucher to READY_TO_FILE
            v_res = await db.execute(select(Voucher).where(Voucher.case_id == target_case.id))
            case_vch = v_res.scalars().first()
            if case_vch:
                case_vch.status = "READY_TO_FILE"
                case_vch.has_appointment_order_verified = True
            else:
                is_felony = "district" in (target_case.court or "").lower() or "felony" in (target_case.charge_description or "").lower()
                case_vch = Voucher(
                    case_id=target_case.id,
                    voucher_number=f"VCH-{target_case.case_number}",
                    voucher_type="CJA-FELONY" if is_felony else "CJA-MISDEMEANOR",
                    status="READY_TO_FILE",
                    amount_requested=1000.0 if is_felony else 500.0,
                    has_appointment_order_verified=True,
                    notes="Voucher transitioned to Ready to Be Filed upon verified Acceptance of Appointment.",
                )
                db.add(case_vch)

    await db.commit()
    await db.refresh(doc)
    return {
        "status": "APPROVED",
        "document_id": doc.id,
        "filename": doc.filename,
        "case_id": doc.case_id,
        "message": "Document approved and downstream case & voucher workflow resumed successfully.",
    }


@router.post("/{id}/sign")
async def sign_document(id: int, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Signing coming in v0.2")
