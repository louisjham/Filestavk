import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from app.database import get_db
from app.deps import get_current_user
from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES
from app.schemas.document_rule import (
    DocumentRuleCreate,
    DocumentRuleUpdate,
    DocumentRuleOut,
)

router = APIRouter()


async def ensure_default_document_rules(db: AsyncSession):
    """Seed default Nueces County legal document rules if missing."""
    res = await db.execute(select(DocumentRule))
    existing_map = {r.document_type: r for r in res.scalars().all()}
    added = False
    for r_dict in DEFAULT_DOCUMENT_RULES:
        doc_type = r_dict["document_type"]
        if doc_type not in existing_map:
            rule = DocumentRule(**r_dict)
            db.add(rule)
            added = True
    if added:
        await db.commit()


@router.get("", response_model=List[DocumentRuleOut])
async def list_document_rules(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all configured static document rules."""
    await ensure_default_document_rules(db)
    query = select(DocumentRule).order_by(DocumentRule.id.asc())
    if active_only:
        query = query.filter(DocumentRule.is_active == True)
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{id_or_type}", response_model=DocumentRuleOut)
async def get_document_rule(
    id_or_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific document rule by ID or by document type."""
    await ensure_default_document_rules(db)
    if id_or_type.isdigit():
        res = await db.execute(select(DocumentRule).where(DocumentRule.id == int(id_or_type)))
    else:
        res = await db.execute(select(DocumentRule).where(DocumentRule.document_type == id_or_type))
    
    rule = res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Document rule '{id_or_type}' not found")
    return rule


@router.post("", response_model=DocumentRuleOut)
async def create_document_rule(
    body: DocumentRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new custom document rule."""
    existing = await db.execute(select(DocumentRule).where(DocumentRule.document_type == body.document_type))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Document rule for '{body.document_type}' already exists")

    rule = DocumentRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{id}", response_model=DocumentRuleOut)
async def update_document_rule(
    id: int,
    body: DocumentRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update an existing static document rule."""
    res = await db.execute(select(DocumentRule).where(DocumentRule.id == id))
    rule = res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Document rule not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(rule, k, v)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{id}")
async def delete_document_rule(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a document rule."""
    res = await db.execute(select(DocumentRule).where(DocumentRule.id == id))
    rule = res.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Document rule not found")

    await db.delete(rule)
    await db.commit()
    return {"status": "deleted", "id": id, "document_type": rule.document_type}


@router.post("/reset-defaults", response_model=List[DocumentRuleOut])
async def reset_default_rules(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Reset all document rules to Nueces County legal defaults."""
    await db.execute(delete(DocumentRule))
    for r_dict in DEFAULT_DOCUMENT_RULES:
        rule = DocumentRule(**r_dict)
        db.add(rule)
    await db.commit()

    res = await db.execute(select(DocumentRule).order_by(DocumentRule.id.asc()))
    return res.scalars().all()


@router.post("/evaluate")
async def evaluate_document_rule(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Evaluate what rules apply to an extracted legal document payload without committing changes.
    Returns preview of predicted stage, client updates, case updates, timeline event, and deadlines.
    """
    doc_type = payload.get("classification_label") or payload.get("document_type") or "uncategorized"
    res = await db.execute(select(DocumentRule).where(DocumentRule.document_type == doc_type))
    rule = res.scalars().first()

    if not rule or not rule.is_active:
        return {
            "has_rule": False,
            "document_type": doc_type,
            "message": f"No active rule configured for category '{doc_type}'. Default fallback will be used."
        }

    legal_meta = payload.get("legal_metadata", payload)
    def_name = legal_meta.get("defendant_name") or "Defendant"
    court = legal_meta.get("court") or "Nueces County Court at Law"
    judge = legal_meta.get("judge") or "Presiding Judge"
    primary_case = legal_meta.get("primary_case_number") or "Unknown Case"
    specialized = legal_meta.get("specialized_fields", {})
    charge = specialized.get("charge_description") or "Pending Offense"
    atty = specialized.get("appointed_attorney") or "Kimbel Brandon"
    sbn = specialized.get("attorney_sbn") or "24079543"

    # Evaluate event title & desc template — guard against unrecognized placeholders in user-edited templates
    template_vars = dict(
        doc_title=rule.display_name,
        court=court,
        judge=judge,
        defendant_name=def_name,
        case_number=primary_case,
        charge=charge,
        attorney_name=atty,
        sbn=sbn,
        amount_paid=specialized.get("amount_paid", "0.00"),
        warrant_number=specialized.get("warrant_number", "N/A"),
        hearing_datetime=specialized.get("hearing_datetime", "Scheduled Date"),
    )
    try:
        event_title = rule.event_title_template.format(**template_vars)
    except KeyError as e:
        event_title = f"{rule.display_name} — {court} (template placeholder {e} not recognized)"
    try:
        event_desc = rule.event_desc_template.format(**template_vars)
    except KeyError as e:
        event_desc = f"Rule description template contains unrecognized placeholder {e}. Please edit the rule template."

    return {
        "has_rule": True,
        "rule_id": rule.id,
        "document_type": rule.document_type,
        "display_name": rule.display_name,
        "lifecycle_stage": rule.lifecycle_stage,
        "target_case_stage": rule.target_case_stage,
        "target_case_status": rule.target_case_status,
        "is_cja": rule.is_cja_default,
        "set_has_appointment_order": rule.set_has_appointment_order,
        "set_appointment_status": rule.set_appointment_status,
        "auto_populate_client": rule.auto_populate_client,
        "client_updates": {
            "dob": specialized.get("dob"),
            "address": specialized.get("address"),
            "phone": specialized.get("phone"),
            "so_number": specialized.get("so_number"),
        } if rule.auto_populate_client else {},
        "auto_populate_case": rule.auto_populate_case,
        "case_updates": {
            "charge_description": charge,
            "court": court,
            "judge": judge,
            "in_custody": specialized.get("in_custody", False),
            "stage": rule.target_case_stage,
            "has_appointment_order": rule.set_has_appointment_order,
            "appointment_status": rule.set_appointment_status,
        } if rule.auto_populate_case else {},
        "create_docket_event": rule.create_docket_event,
        "predicted_event": {
            "event_type": rule.event_type,
            "title": event_title,
            "description": event_desc,
        } if rule.create_docket_event else None,
        "trigger_statutory_deadline": rule.trigger_statutory_deadline,
        "statutory_deadline": {
            "name": rule.deadline_name,
            "statutory_basis": rule.statutory_basis,
            "hours_offset": rule.deadline_hours_offset,
        } if rule.trigger_statutory_deadline else None,
    }
