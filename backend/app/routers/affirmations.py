"""
FastAPI router for Kimbel's Daily Cephalopod Affirmations and Practice Encouragement.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.deps import get_current_user
from app.services.affirmation_service import affirmation_service

router = APIRouter()


@router.get("/daily")
async def get_daily_affirmation(
    date: Optional[str] = Query(None, description="Optional target date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
):
    """Returns today's stable, deterministic affirmation and greeting for Kimbel."""
    return affirmation_service.get_daily_affirmation(target_date=date)


@router.get("/random")
async def get_random_affirmation(
    current_user: dict = Depends(get_current_user),
):
    """Returns a fresh random affirmation on demand."""
    return affirmation_service.get_random_affirmation()
