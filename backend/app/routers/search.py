from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.classification import SearchHistory
from app.deps import get_current_user

router = APIRouter()

@router.get("/canned")
async def get_canned(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).filter(SearchHistory.pinned == True))
    return res.scalars().all()

@router.post("/execute")
async def execute_search(query_text: str, filters_json: str = "{}", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    sh = SearchHistory(query_text=query_text, filters_json=filters_json, result_count=0)
    db.add(sh)
    await db.commit()
    await db.refresh(sh)
    return sh

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).order_by(SearchHistory.executed_at.desc()).limit(10))
    return res.scalars().all()

@router.patch("/history/{id}/pin")
async def pin_search(id: int, pinned: bool, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    res = await db.execute(select(SearchHistory).filter(SearchHistory.id == id))
    sh = res.scalars().first()
    if sh:
        sh.pinned = pinned
        await db.commit()
    return sh
