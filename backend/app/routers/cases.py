from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseOut, CaseUpdate
from app.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[CaseOut])
async def get_cases(status: str = None, is_cja: bool = None, client_id: int = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    query = select(Case)
    if status: query = query.filter(Case.status == status)
    if is_cja is not None: query = query.filter(Case.is_cja == is_cja)
    if client_id: query = query.filter(Case.client_id == client_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=CaseOut)
async def create_case(case: CaseCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if case.case_number:
        res = await db.execute(select(Case).filter(Case.case_number == case.case_number))
        existing_case = res.scalars().first()
        if existing_case:
            # Update non-empty fields
            c_data = case.model_dump(exclude_unset=True)
            for k, v in c_data.items():
                if v is not None:
                    setattr(existing_case, k, v)
            await db.commit()
            await db.refresh(existing_case)
            return existing_case

    new_case = Case(**case.model_dump())
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    return new_case

@router.get("/{id}")
async def get_case(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Case).filter(Case.id == id))
    case = result.scalars().first()
    if not case: raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.patch("/{id}")
async def update_case(id: int, case: CaseUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Case).filter(Case.id == id))
    db_case = result.scalars().first()
    if not db_case: raise HTTPException(status_code=404, detail="Case not found")
    for key, value in case.model_dump(exclude_unset=True).items():
        setattr(db_case, key, value)
    await db.commit()
    await db.refresh(db_case)
    return db_case

from app.models.event import Event
from app.models.document import Document

@router.get("/{id}/timeline")
async def case_timeline(id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res_case = await db.execute(select(Case).filter(Case.id == id))
    case = res_case.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    res_events = await db.execute(select(Event).filter(Event.case_id == id).order_by(Event.event_date.asc(), Event.id.asc()))
    events = res_events.scalars().all()

    res_docs = await db.execute(select(Document).filter(Document.case_id == id).order_by(Document.id.asc()))
    docs = res_docs.scalars().all()

    return {
        "case_id": id,
        "case_number": case.case_number,
        "events": events,
        "documents": docs,
    }

from pydantic import BaseModel
from app.services.odyssey_timeline_parser import parse_odyssey_timeline

class TimelineImportRequest(BaseModel):
    raw_text: str

class SingleEventCreateRequest(BaseModel):
    title: str
    event_type: Optional[str] = "DOCKET_EVENT"
    description: Optional[str] = None
    event_date: Optional[str] = None

@router.post("/{id}/import-portal-timeline")
async def import_portal_timeline(
    id: int,
    payload: TimelineImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Parse an Odyssey Portal case summary, docket history, or narrative
    and batch insert structured chronological events into the case timeline.
    """
    res_case = await db.execute(select(Case).filter(Case.id == id))
    case = res_case.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    parsed_events = parse_odyssey_timeline(payload.raw_text)
    if not parsed_events:
        raise HTTPException(status_code=400, detail="Could not detect any chronological events from the provided text.")

    created = []
    for ev_data in parsed_events:
        event = Event(
            case_id=id,
            title=ev_data["title"],
            event_type=ev_data["event_type"],
            description=ev_data["description"],
            event_date=ev_data["event_date"],
        )
        db.add(event)
        created.append({
            "title": event.title,
            "event_type": event.event_type,
            "event_date": event.event_date,
            "description": event.description,
        })

    await db.commit()
    return {
        "status": "success",
        "message": f"Successfully imported {len(created)} timeline events from Odyssey Portal summary.",
        "events_count": len(created),
        "events": created,
    }

@router.post("/{id}/events")
async def add_case_event(
    id: int,
    payload: SingleEventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a single manual event to the case timeline."""
    res_case = await db.execute(select(Case).filter(Case.id == id))
    case = res_case.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    event = Event(
        case_id=id,
        title=payload.title,
        event_type=payload.event_type or "DOCKET_EVENT",
        description=payload.description,
        event_date=payload.event_date or datetime.now().strftime("%Y-%m-%d"),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/{id}/events/{event_id}")
async def delete_case_event(
    id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a single event from the case timeline."""
    res_ev = await db.execute(select(Event).filter(Event.id == event_id, Event.case_id == id))
    ev = res_ev.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(ev)
    await db.commit()
    return {"status": "success", "message": "Event deleted successfully"}

from datetime import datetime, timedelta, timezone
from app.models.client import Client

@router.get("/{id}/appellate-extension-draft")
async def get_appellate_extension_draft(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a file-ready Texas 13th Court of Appeals Motion to Extend Time for Filing Appellant's Brief
    (Tex. R. App. P. 10.5(b) & 38.6(d)) pre-populated with case docket information.
    """
    res = await db.execute(
        select(Case, Client)
        .outerjoin(Client, Case.client_id == Client.id)
        .where(Case.id == id)
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    case_obj, client_obj = row
    client_name = client_obj.name if client_obj else "Appellant"
    appellate_cause = case_obj.appellate_case_number or case_obj.case_number or "13-26-00155-CR"
    trial_court_no = case_obj.trial_court_case_number or case_obj.case_number or "N/A"
    
    current_count = case_obj.appellate_extension_count or 1
    next_count = current_count + 1
    seq_str = "FIRST" if next_count == 1 else "SECOND" if next_count == 2 else "THIRD" if next_count == 3 else f"{next_count}TH"
    seq_title = seq_str.title()

    # Dates
    today_dt = datetime.now(timezone.utc).date()
    today_formatted = today_dt.strftime("%B %d, %Y")

    if case_obj.appellate_brief_due_date:
        try:
            prior_due_dt = datetime.strptime(case_obj.appellate_brief_due_date[:10], "%Y-%m-%d").date()
            prior_due_formatted = prior_due_dt.strftime("%B %d, %Y")
        except Exception:
            prior_due_dt = today_dt
            prior_due_formatted = case_obj.appellate_brief_due_date
    else:
        prior_due_dt = today_dt
        prior_due_formatted = today_formatted

    req_due_dt = prior_due_dt + timedelta(days=30)
    req_due_formatted = req_due_dt.strftime("%B %d, %Y")

    reason_text = case_obj.appellate_extension_reason or (
        "Several weeks ago, counsel for Appellant unexpectedly lost the assistance of her administrative assistant, "
        "who remains on extended FMLA leave. The resulting loss of support staff has caused unexpected delays in "
        "counsel's ability to complete and file Appellant's Brief."
    )

    pleading_text = f"""NO. {appellate_cause}

IN THE
COURT OF APPEALS
13TH SUPREME JUDICIAL DISTRICT OF TEXAS
AT CORPUS CHRISTI - EDINBURG

{client_name.upper()}
Appellant,
v.
THE STATE OF TEXAS
Appellee.

{seq_str} MOTION TO EXTEND TIME FOR
FILING APPELLANT'S BRIEF

TO THE HONORABLE COURT OF APPEALS:
{client_name}, Appellant, moves this Court to grant a {seq_title.lower()} extension of time to file Appellant's brief, and respectfully states:

I. Appellant's Brief was previously due to be filed with this Court on {prior_due_formatted}, pursuant to this Court's prior schedule/extension. This is Appellant's {seq_title.lower()} request for an extension.

II. Appellant seeks an additional 30-day extension of time to file Appellant's Brief, which would make Appellant's Brief due on or before {req_due_formatted}.

III. {reason_text}

IV. This extension of time is necessary to ensure justice is done and is not intended to cause unnecessary delay.

V. Counsel for Appellant has conferred with counsel for the State of Texas, and the State of Texas is not opposed to this request.

Appellant respectfully requests that this Court render an order extending the time for filing Appellant's Brief to and including {req_due_formatted}. Appellant also requests any other relief to which he may be entitled.

Respectfully Submitted,

HEMOCYANIN LAW LLC
1535 15th Street
Corpus Christi, Texas 78404

/s/ Kimbel Brandon
Kimbel Brandon
Appellate Counsel
State Bar No. 24079543
kimbelfbrandon@gmail.com
(361) 737-2625 (o) | (661) 649-0356 (c)


CERTIFICATE OF CONFERENCE
This certifies that the undersigned counsel for {client_name}, Appellant, has conferred with counsel for the Appellee regarding the merits of this motion, and the Appellee is not opposed to the granting of this request.

/s/ Kimbel Brandon
Kimbel Brandon


CERTIFICATE OF SERVICE
I certify that a true and correct copy of the foregoing motion will be filed and served electronically on counsel for the State of Texas through the Court's electronic filing system today, {today_formatted}.

/s/ Kimbel Brandon
Kimbel Brandon
"""

    return {
        "case_id": id,
        "appellate_case_number": appellate_cause,
        "trial_court_case_number": trial_court_no,
        "client_name": client_name,
        "motion_sequence": seq_str,
        "prior_due_date": prior_due_formatted,
        "requested_due_date": req_due_formatted,
        "extension_days": 30,
        "good_cause_statement": reason_text,
        "opposing_status": "Unopposed",
        "service_date": today_formatted,
        "draft_pleading_text": pleading_text.strip(),
    }

