from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.deps import get_current_user
from app.database import get_db
from app.models.classification import PortalAuditLog
from app.services.portal_service import start_portal_lookup, get_job_status, cancel_job, resume_job

router = APIRouter()


class PortalLookupRequest(BaseModel):
    search_type: str = "case_number"  # "case_number" or "name"
    search_query: str
    case_id: Optional[int] = None
    client_id: Optional[int] = None


@router.post("/lookup")
async def create_portal_lookup(
    body: PortalLookupRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start an on-demand Nueces County Odyssey Smart Search portal lookup."""
    query = body.search_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    if body.search_type not in ("case_number", "name"):
        raise HTTPException(status_code=400, detail="search_type must be 'case_number' or 'name'")

    job_id = start_portal_lookup(
        search_type=body.search_type,
        search_query=query,
        case_id=body.case_id,
        client_id=body.client_id
    )

    return {"job_id": job_id, "status": "PENDING", "message": "Browser launch initiated"}


@router.get("/jobs/{job_id}")
async def get_portal_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll live status of a portal lookup job."""
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/resume")
async def resume_portal_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Signal that the human has solved the CAPTCHA and the agent should proceed."""
    success = resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be resumed or has already proceeded")
    return {"status": "SEARCHING", "message": "Resume signal processed"}


@router.post("/jobs/{job_id}/cancel")
async def cancel_portal_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a running portal assist job."""
    success = cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job could not be cancelled or has already completed")
    return {"status": "CANCELLED"}


@router.get("/audit-logs")
async def get_portal_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve recent portal lookup audit records."""
    result = await db.execute(
        select(PortalAuditLog).order_by(PortalAuditLog.id.desc()).limit(20)
    )
    logs = result.scalars().all()
    return logs
