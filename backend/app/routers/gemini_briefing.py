"""
FastAPI router for Kimbel Brandon's Gemini 10-Day Deep-Dive Brief Ingestion & Auto-Population.
Handles pasting raw brief text, deterministic parsing, staging, and atomic DB commitment.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.deps import get_current_user
from app.database import get_db
from app.models.case import Case
from app.models.client import Client
from app.models.event import Event
from app.models.time_entry import Voucher
from app.services.gemini_brief_parser_service import gemini_brief_parser_service

logger = logging.getLogger(__name__)

router = APIRouter()

BRIEF_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "latest_gemini_brief.json"
)


class PasteBriefRequest(BaseModel):
    raw_text: str


class CommitProposalsRequest(BaseModel):
    proposals: List[Dict[str, Any]]
    verified_by: Optional[str] = "Kimbel Brandon, Esq."


@router.post("/paste")
async def paste_gemini_brief(
    payload: PasteBriefRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Accepts raw text pasted from Kimbel's Gemini 10-Day Deep-Dive Brief.
    Runs deterministic extraction, persists to data/latest_gemini_brief.json,
    and returns parsed action items for the Verification Board.
    """
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Pasted brief content cannot be empty.")

    parsed = gemini_brief_parser_service.parse_brief(payload.raw_text)

    # Persist latest brief state to disk
    os.makedirs(os.path.dirname(BRIEF_STORAGE_PATH), exist_ok=True)
    with open(BRIEF_STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "message": f"Successfully parsed {parsed['summary_counts']['total_items']} items from Gemini Deep-Dive Brief.",
        "summary_counts": parsed["summary_counts"],
        "conflicts": parsed["conflicts"],
        "proposals": parsed["proposals"],
        "parsed_at": parsed["parsed_at"],
        "raw_text": parsed["raw_text"],
    }


@router.get("/latest")
async def get_latest_brief(
    current_user: dict = Depends(get_current_user),
):
    """Returns the most recently ingested Gemini Deep-Dive Brief and its verification proposals."""
    if not os.path.exists(BRIEF_STORAGE_PATH):
        return {
            "has_brief": False,
            "raw_text": "",
            "summary_counts": {"total_items": 0},
            "conflicts": [],
            "proposals": [],
        }

    try:
        with open(BRIEF_STORAGE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["has_brief"] = True
        return data
    except Exception as e:
        logger.error(f"Failed to read latest_gemini_brief.json: {e}")
        return {
            "has_brief": False,
            "error": str(e),
            "proposals": [],
        }


@router.post("/commit")
async def commit_brief_proposals(
    payload: CommitProposalsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Atomic Human Verification Commit Action for Gemini Brief Proposals.
    Populates Cases, Clients, Events, and Vouchers across the database.
    """
    proposals = payload.proposals
    if not proposals:
        raise HTTPException(status_code=400, detail="No proposals submitted for verification.")

    created_cases = []
    updated_cases = []
    created_events = []
    created_clients = []
    updated_vouchers = []

    for item in proposals:
        case_num = (item.get("case_number") or "").strip()
        client_name = (item.get("client_name") or "").strip()
        court = (item.get("court") or "347th District Court").strip()
        judge = item.get("judge")
        action_type = item.get("action_type")
        category = item.get("category")
        event_date = item.get("event_date") or datetime.now().strftime("%Y-%m-%d")
        details = item.get("details") or ""
        in_custody = item.get("in_custody", False)
        charge = item.get("charge")
        stage = item.get("stage") or "DISCOVERY"

        # 1. Match or Create Client
        client = None
        if client_name and client_name != "Unknown Client":
            client_res = await db.execute(select(Client).where(Client.name.ilike(f"%{client_name}%")))
            client = client_res.scalars().first()
            if not client:
                client = Client(
                    name=client_name,
                    notes=f"Created via Gemini Brief Ingestion ({datetime.now().strftime('%Y-%m-%d')})"
                )
                db.add(client)
                await db.flush()
                created_clients.append(client.name)

        # 2. Match or Create Case
        case = None
        if case_num and case_num != "Cause # Not Provided":
            case_res = await db.execute(select(Case).where(Case.case_number == case_num))
            case = case_res.scalars().first()

            if not case:
                case = Case(
                    case_number=case_num,
                    client_id=client.id if client else None,
                    court=court,
                    judge=judge,
                    stage=stage,
                    status="OPEN",
                    in_custody=in_custody,
                    charge_description=charge or f"Matter in {court}",
                    opened_date=datetime.now().strftime("%Y-%m-%d"),
                    notes=f"Ingested from Gemini 10-Day Brief on {datetime.now().strftime('%Y-%m-%d')}. {details[:200]}"
                )
                if category == "CRITICAL_DEADLINE" and "appointment" in item.get("title", "").lower():
                    case.has_appointment_order = True
                    case.appointment_status = "AWAITING_ACCEPTANCE"
                    case.appointment_order_date = event_date

                db.add(case)
                await db.flush()
                created_cases.append(case.case_number)
            else:
                # Update existing case details
                if court and court != "Nueces County District Court":
                    case.court = court
                if judge:
                    case.judge = judge
                if in_custody:
                    case.in_custody = True
                if charge and not case.charge_description:
                    case.charge_description = charge
                if stage and stage in ("PRE_TRIAL", "APPEAL") and case.stage in ("INTAKE", "UNKNOWN"):
                    case.stage = stage

                updated_cases.append(case.case_number)

        # 3. Schedule Docket Event
        if category in ("COURT_HEARING", "CRITICAL_DEADLINE", "CASE_UPDATE", "APPELLATE_ORDER"):
            ev_type = "HEARING"
            if category == "CRITICAL_DEADLINE":
                ev_type = "APPOINTMENT_ORDER" if "appointment" in item.get("title", "").lower() else "DEADLINE"
            elif action_type == "RECORD_WAIVER":
                ev_type = "WAIVER_OF_ARRAIGNMENT"
            elif category == "APPELLATE_ORDER":
                ev_type = "APPELLATE_ORDER"

            event_title = item.get("title") or f"{ev_type}: {client_name}"
            event_desc = f"{details} [Verified by {payload.verified_by}]"
            if item.get("has_conflict"):
                event_desc = f"⚠️ DOCKET CONFLICT: {item.get('conflict_note')} | " + event_desc

            # Avoid exact duplicate event on same date
            ev_check = await db.execute(
                select(Event).where(
                    Event.case_id == (case.id if case else None),
                    Event.event_date == event_date,
                    Event.event_type == ev_type
                )
            )
            if not ev_check.scalars().first():
                event = Event(
                    case_id=case.id if case else None,
                    event_type=ev_type,
                    title=event_title,
                    description=event_desc,
                    event_date=event_date,
                )
                db.add(event)
                created_events.append(event_title)

        # 4. Process Vouchers if category == VOUCHER_STATUS
        if category == "VOUCHER_STATUS" and case:
            v_res = await db.execute(select(Voucher).where(Voucher.case_id == case.id))
            voucher = v_res.scalars().first()
            if voucher:
                if item.get("status"):
                    voucher.status = item["status"]
                if item.get("amount"):
                    voucher.amount_approved = item["amount"]
                if item.get("warrant_number"):
                    voucher.warrant_number = item["warrant_number"]
                updated_vouchers.append(voucher.voucher_number or f"Voucher-{voucher.id}")

    await db.commit()

    return {
        "status": "success",
        "message": f"Successfully verified & committed {len(proposals)} items into Filestavk.",
        "committed_total": len(proposals),
        "created_cases": created_cases,
        "updated_cases": list(set(updated_cases)),
        "created_clients": created_clients,
        "created_events": created_events,
        "updated_vouchers": updated_vouchers,
    }


@router.put("/proposals/{index}")
async def update_brief_proposal(
    index: int,
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Update a specific proposal in the staged Gemini brief."""
    if not os.path.exists(BRIEF_STORAGE_PATH):
        raise HTTPException(status_code=404, detail="No active Gemini brief found.")

    with open(BRIEF_STORAGE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    proposals = data.get("proposals", [])
    if index < 0 or index >= len(proposals):
        raise HTTPException(status_code=404, detail="Proposal index out of range.")

    proposals[index].update(payload)
    data["proposals"] = proposals

    with open(BRIEF_STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"status": "success", "proposal": proposals[index]}


@router.delete("/proposals/{index}")
async def delete_brief_proposal(
    index: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a specific proposal from the staged Gemini brief."""
    if not os.path.exists(BRIEF_STORAGE_PATH):
        raise HTTPException(status_code=404, detail="No active Gemini brief found.")

    with open(BRIEF_STORAGE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    proposals = data.get("proposals", [])
    if index < 0 or index >= len(proposals):
        raise HTTPException(status_code=404, detail="Proposal index out of range.")

    removed = proposals.pop(index)
    data["proposals"] = proposals
    data["summary_counts"]["total_items"] = len(proposals)

    with open(BRIEF_STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"status": "success", "removed": removed}
