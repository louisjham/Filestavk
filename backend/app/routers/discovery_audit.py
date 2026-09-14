"""
FastAPI router for Michael Morton Act (Art. 39.14 CCP) Discovery Audit & Motion Generation.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.services.discovery_audit_service import discovery_audit_service

router = APIRouter(prefix="/cases", tags=["discovery_audit"])


@router.post("/{case_id}/discovery-audit")
async def run_discovery_audit(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Executes the Michael Morton Art. 39.14 Red Ink Discovery Gap Audit for a case."""
    report = await discovery_audit_service.audit_case_discovery(db, case_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report


@router.get("/{case_id}/discovery-audit")
async def get_discovery_audit(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns the cached or newly evaluated discovery gap audit for a case."""
    report = await discovery_audit_service.audit_case_discovery(db, case_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report


@router.get("/{case_id}/discovery-deficit-motion", response_class=PlainTextResponse)
async def generate_motion_to_compel_endpoint(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generates file-ready text for an Art. 39.14 Notice of Discovery Deficit & Motion to Compel."""
    report = await discovery_audit_service.audit_case_discovery(db, case_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    motion_text = discovery_audit_service.generate_motion_to_compel(report)
    return motion_text
