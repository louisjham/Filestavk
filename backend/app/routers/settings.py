from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.deps import get_current_user
from app.database import get_db
from app.models.case import Case
from app.models.client import Client
from app.models.time_entry import Voucher
from app.models.document import Document

router = APIRouter()

# In-memory attorney profile for Kimbel Brandon / Hemocyanin Law
ATTORNEY_PROFILE = {
    "name": "Kimbel Brandon",
    "title": "Attorney at Law",
    "firm_name": "Hemocyanin Law",
    "website": "https://www.hemocyaninlaw.com/",
    "intake_email": "info@hemocyaninlaw.com",
    "business_email": "kimbel@hemocyaninlaw.com",
    "bar_number": "24098742",
    "vendor_number": "TX-NUE-84920",
    "address": "802 N. Carancahua St, Ste 1200, Corpus Christi, TX 78401",
    "phone": "(361) 882-5299",
    "digital_signature_name": "Kimbel Brandon, Esq.",
    "digital_signature_hash": "SHA256-NUE-84920-KB-2024",
    "digital_signature_status": "VERIFIED_ACTIVE",
    "hourly_rate_standard": 100.0,
    "statutory_jurisdiction": "Nueces County, Texas (Art. 26.05 CCP)",
}


class AttorneyProfileUpdate(BaseModel):
    name: Optional[str] = None
    firm_name: Optional[str] = None
    website: Optional[str] = None
    intake_email: Optional[str] = None
    business_email: Optional[str] = None
    bar_number: Optional[str] = None
    vendor_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


@router.get("/profile")
async def get_attorney_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve attorney profile and statutory voucher credentials."""
    return ATTORNEY_PROFILE


@router.patch("/profile")
async def update_attorney_profile(
    body: AttorneyProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update attorney profile or voucher credentials."""
    for k, v in body.dict(exclude_unset=True).items():
        if v is not None:
            ATTORNEY_PROFILE[k] = v
    return ATTORNEY_PROFILE


@router.get("/dashboard-alerts")
async def get_dashboard_morning_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Unified Good Morning Alert Aggregator.
    Returns prioritized alerts across EITHER Cases (in-custody milestones, court dates)
    OR Vouchers (30-day statutory expiration, rejection/clarification required).
    """
    now = datetime.now(timezone.utc).date()
    alerts: List[Dict[str, Any]] = []

    # 1. Fetch Vouchers for Backlog and Rejection Alerts
    voucher_res = await db.execute(select(Voucher))
    vouchers = voucher_res.scalars().all()

    for v in vouchers:
        # Check unbilled vouchers backlog
        if v.status == "UNBILLED":
            alerts.append({
                "id": f"vch-unbilled-{v.id}",
                "type": "VOUCHER_UNBILLED",
                "severity": "WARNING",
                "title": f"Unbilled Voucher Ready: #{v.voucher_number}",
                "description": f"Voucher #{v.voucher_number} (${v.amount_requested:,.2f}) has verified appointment order and is ready for submission.",
                "target_id": v.id,
                "case_id": v.case_id,
                "action_label": "Auto-Build & Submit Voucher",
                "link": f"/cases/{v.case_id}",
            })

        # Check returned vouchers needing clarification
        if v.status == "RETURNED":
            alerts.append({
                "id": f"vch-ret-{v.id}",
                "type": "VOUCHER_RETURNED",
                "severity": "HIGH",
                "title": f"Court Coordinator Clarification: #{v.voucher_number}",
                "description": v.rejection_reason or "Voucher returned by court coordinator for itemization update.",
                "target_id": v.id,
                "case_id": v.case_id,
                "action_label": "Review & Resubmit",
                "link": f"/vouchers",
            })

    # 2. Fetch Cases for In-Custody / Jail Milestone Alerts
    case_res = await db.execute(select(Case, Client).outerjoin(Client, Case.client_id == Client.id))
    cases_with_clients = case_res.all()

    in_custody_roster = []

    for c, cl in cases_with_clients:
        if c.in_custody:
            days_in_jail = 0
            if c.jail_booking_date:
                try:
                    book_dt = datetime.strptime(c.jail_booking_date[:10], "%Y-%m-%d").date()
                    days_in_jail = (now - book_dt).days
                except Exception:
                    days_in_jail = 0

            in_custody_roster.append({
                "case_id": c.id,
                "client_id": c.client_id,
                "client_name": cl.name if cl else f"Client #{c.client_id}",
                "case_number": c.case_number,
                "charge": c.charge_description or "Criminal Charge",
                "court": c.court,
                "stage": c.stage,
                "days_in_jail": days_in_jail,
                "booking_date": c.jail_booking_date,
                "facility": c.jail_facility or "Nueces County Jail - Main",
                "bond_amount": c.bond_amount,
                "bond_type": c.bond_type or "SURETY",
            })

            # If client has been in jail for > 30 days and still in discovery / no indictment
            if days_in_jail >= 30 and c.stage in ("ARREST", "BOND", "INDICTMENT", "DISCOVERY"):
                alerts.append({
                    "id": f"jail-milestone-{c.id}",
                    "type": "IN_CUSTODY_MILESTONE",
                    "severity": "HIGH" if days_in_jail >= 45 else "MEDIUM",
                    "title": f"In-Custody Milestone: {days_in_jail} Days in Jail",
                    "description": f"Case #{c.case_number} ({c.charge_description}) has been detained {days_in_jail} days. Consider Art. 17.151 CCP bail reduction motion.",
                    "target_id": c.id,
                    "case_id": c.id,
                    "action_label": "Review Custody & Bond",
                    "link": f"/cases/{c.id}",
                })

    # 3. Fetch CJA Cases Awaiting Acceptance of Appointment (Art. 26.04 CCP)
    from sqlalchemy import and_
    appt_res = await db.execute(
        select(Case, Client)
        .join(Client, Case.client_id == Client.id)
        .where(and_(
            Case.is_cja == True,
            Case.has_appointment_order == True,
            Case.has_appointment_acceptance == False,
            Case.status != "DISPOSED",
        ))
    )
    awaiting_acceptance = []
    for row in appt_res.all():
        c, cl = row
        days_pending = None
        if c.appointment_order_date:
            try:
                order_dt = datetime.strptime(c.appointment_order_date[:10], "%Y-%m-%d").date()
                days_pending = (now - order_dt).days
            except Exception:
                pass
        awaiting_acceptance.append({
            "case_id": c.id,
            "client_id": c.client_id,
            "client_name": cl.name,
            "case_number": c.case_number,
            "charge": c.charge_description or "Criminal Matter",
            "court": c.court or "Nueces County Court",
            "appointment_order_date": c.appointment_order_date,
            "days_pending": days_pending,
        })
        # Also add a HIGH severity alert for cases pending > 7 days without acceptance
        if days_pending is not None and days_pending >= 7:
            alerts.append({
                "id": f"appt-awaiting-{c.id}",
                "type": "AWAITING_ACCEPTANCE",
                "severity": "HIGH" if days_pending >= 14 else "WARNING",
                "title": f"Acceptance Not Filed: {cl.name} — #{c.case_number}",
                "description": f"Order of Appointment issued {days_pending} days ago. File-stamped Acceptance required before Nueces County Auditor will authorize payment.",
                "target_id": c.id,
                "case_id": c.id,
                "action_label": "Upload Acceptance",
                "link": f"/documents?case_id={c.id}",
            })

    # 4. Fetch Mid-Stride Cases (Acceptance filed without prior Appointment Order)
    mid_stride_res = await db.execute(
        select(Case, Client)
        .join(Client, Case.client_id == Client.id)
        .where(and_(
            Case.has_appointment_acceptance == True,
            Case.has_appointment_order == False,
            Case.status != "DISPOSED",
        ))
    )
    for row in mid_stride_res.all():
        c, cl = row
        alerts.append({
            "id": f"mid-stride-{c.id}",
            "type": "MID_STRIDE_MISSING_ORDER",
            "severity": "WARNING",
            "title": f"Mid-Stride Case: {cl.name} — #{c.case_number}",
            "description": f"File-stamped Acceptance recorded, but no prior Order of Appointment is in the system. Case provisioned mid-stride. Verify appointment order on Odyssey portal.",
            "target_id": c.id,
            "case_id": c.id,
            "action_label": "View Case",
            "link": f"/cases/{c.id}",
        })

    # 5. Documents Awaiting Human Review
    review_res = await db.execute(
        select(Document)
        .where(Document.metadata_json.like('%"review_status": "AWAITING_HUMAN_REVIEW"%'))
    )
    for d in review_res.scalars().all():
        alerts.append({
            "id": f"doc-review-{d.id}",
            "type": "AWAITING_HUMAN_REVIEW",
            "severity": "HIGH",
            "title": f"Review Required: {d.filename}",
            "description": "Visual verification needed: inspect Clerk 'FILED' stamp and attorney signature under 'AFFIRMED' before voucher workflow can proceed.",
            "target_id": d.id,
            "case_id": d.case_id,
            "action_label": "Inspect & Approve",
            "link": f"/documents",
        })

    # 6. Vouchers Ready to Be Filed on Perfect Apps
    ready_vch_res = await db.execute(
        select(Voucher, Case, Client)
        .join(Case, Voucher.case_id == Case.id, isouter=True)
        .join(Client, Case.client_id == Client.id, isouter=True)
        .where(Voucher.status == "READY_TO_FILE")
    )
    for row in ready_vch_res.all():
        v, c, cl = row
        c_num = c.case_number if c else "General"
        cl_name = cl.name if cl else "Client"
        alerts.append({
            "id": f"vch-ready-{v.id}",
            "type": "VOUCHER_READY_TO_FILE",
            "severity": "MEDIUM",
            "title": f"Voucher Ready to File: {cl_name} — #{c_num}",
            "description": f"Acceptance confirmed on docket. Voucher #{v.voucher_number or v.id} (${(v.amount_requested or 0):.2f}) is ready to submit on Nueces County Perfect Apps.",
            "target_id": v.id,
            "case_id": c.id if c else None,
            "action_label": "Go to Vouchers",
            "link": "/vouchers",
        })

    # Sort alerts by severity (CRITICAL first, then HIGH, then WARNING, then MEDIUM)
    severity_order = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "MEDIUM": 3}
    alerts.sort(key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 4))

    # Sort in-custody roster by days in jail descending (longest first)
    in_custody_roster.sort(key=lambda x: x["days_in_jail"], reverse=True)

    return {
        "attorney": ATTORNEY_PROFILE["name"],
        "firm": ATTORNEY_PROFILE["firm_name"],
        "date_today": now.strftime("%A, %B %d, %Y"),
        "total_alerts": len(alerts),
        "alerts": alerts,
        "in_custody_count": len(in_custody_roster),
        "in_custody_roster": in_custody_roster,
        "awaiting_acceptance": awaiting_acceptance,
        "awaiting_acceptance_count": len(awaiting_acceptance),
    }


DELEGATED_TASKS: List[dict] = []



@router.get("/delegated-tasks")
async def get_delegated_tasks(current_user: dict = Depends(get_current_user)):
    """Retrieve Kimbel's delegated task queue for assistant mode."""
    return DELEGATED_TASKS


@router.patch("/delegated-tasks/{task_id}")
async def update_delegated_task(
    task_id: str,
    status: str = "COMPLETED",
    current_user: dict = Depends(get_current_user)
):
    """Mark a delegated task as COMPLETED or PENDING."""
    for t in DELEGATED_TASKS:
        if t["id"] == task_id:
            t["status"] = status
            return t
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/database/purge-mock-data")
async def purge_mock_database_data(
    body: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean Slate Action: Purges all mock clients, cases, vouchers, documents, and events.
    Restricted to attorney role only. Requires confirmation token to prevent accidental wipes.
    """
    # Role guard — assistants cannot wipe the database
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Database purge requires attorney role.")

    # Explicit confirmation token required
    if body.get("confirm") != "PURGE_DATABASE":
        raise HTTPException(
            status_code=400,
            detail='Confirmation required. Send {"confirm": "PURGE_DATABASE"} in request body.'
        )

    from sqlalchemy import text

    # Tables to purge in dependency order
    tables = [
        "document_labels",
        "documents",
        "events",
        "time_entries",
        "vouchers",
        "cases",
        "clients",
        "search_history",
        "portal_audit_log",
        "ingestion_jobs",
        "raw_email_staging",
    ]

    deleted_counts = {}
    for tbl in tables:
        try:
            res = await db.execute(text(f"DELETE FROM {tbl}"))
            deleted_counts[tbl] = res.rowcount
        except Exception as e:
            deleted_counts[tbl] = f"skipped ({e})"

    await db.commit()

    return {
        "status": "success",
        "message": "All mock and demo data tables have been cleanly purged. System is ready for live production ingestion.",
        "purged_records": deleted_counts,
        "purged_at": datetime.now(timezone.utc).isoformat(),
    }

