from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
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

    res_events = await db.execute(select(Event).filter(Event.case_id == id).order_by(Event.id.asc()))
    events = res_events.scalars().all()

    res_docs = await db.execute(select(Document).filter(Document.case_id == id).order_by(Document.id.asc()))
    docs = res_docs.scalars().all()

    return {
        "case_id": id,
        "case_number": case.case_number,
        "events": events,
        "documents": docs,
    }

@router.post("/{id}/ai-analyze")
async def ai_analyze(id: int, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="AI analysis coming in v0.2")

@router.post("/vouchers/{id}/submit-evoucher")
async def submit_evoucher(id: int, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="eVoucher coming in v0.2")
