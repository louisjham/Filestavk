from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from app.deps import get_current_user
from app.database import get_db
from app.models.case import Case
from app.models.document import Document
from app.models.time_entry import Voucher

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Active cases
    active_cases_res = await db.execute(select(func.count(Case.id)).where(Case.status == "open"))
    active_cases = active_cases_res.scalar() or 0

    # Open CJA cases
    open_cja_res = await db.execute(select(func.count(Case.id)).where(Case.is_cja == True, Case.status == "open"))
    open_cja = open_cja_res.scalar() or 0

    # Total documents
    docs_res = await db.execute(select(func.count(Document.id)))
    docs_count = docs_res.scalar() or 0

    # Unclassified documents
    unclass_res = await db.execute(
        select(func.count(Document.id)).where(
            or_(
                Document.classification_label == "uncategorized",
                Document.classification_label == None,
                Document.classification_label == "",
            )
        )
    )
    unclass_count = unclass_res.scalar() or 0

    # Pending / unbilled vouchers
    vouchers_res = await db.execute(
        select(func.count(Voucher.id)).where(
            Voucher.status.in_(["UNBILLED", "SUBMITTED", "PENDING", "DRAFT"])
        )
    )
    vouchers_pending = vouchers_res.scalar() or 0

    return {
        "active_cases": active_cases,
        "open_cja_cases": open_cja,
        "documents_this_month": docs_count,
        "unclassified_docs": unclass_count,
        "vouchers_pending": vouchers_pending,
    }

@router.get("/cases-by-month")
async def cases_by_month(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return []

@router.get("/doc-type-distribution")
async def doc_type_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    res = await db.execute(
        select(Document.classification_label, func.count(Document.id)).group_by(Document.classification_label)
    )
    dist = {}
    for label, count in res.all():
        dist[label or "uncategorized"] = count
    return dist

