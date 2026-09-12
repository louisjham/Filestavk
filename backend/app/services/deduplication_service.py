"""
Deduplication & Entity Consolidation Service.
Finds duplicate clients and cases (created via multiple ingestions, raw text imports, or test runs),
merges their child relationships (cases, documents, events, vouchers, time entries),
consolidates demographic and contact metadata, and deletes redundant orphaned records.
"""

import re
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete, update

from app.models.client import Client
from app.models.case import Case
from app.models.document import Document
from app.models.event import Event
from app.models.time_entry import Voucher, TimeEntry

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalizes names for matching: strips punctuation, lowercase, single-spaced."""
    if not name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", name).lower()
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_case_number(case_num: str) -> str:
    """Normalizes case/cause numbers for matching."""
    if not case_num:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", case_num).upper().strip()


async def run_full_database_deduplication(db: AsyncSession) -> Dict[str, Any]:
    """
    Performs complete deduplication and reconciliation across clients and cases in SQLite.
    Returns a summary of merged records and updated relations.
    """
    # -------------------------------------------------------------
    # 1. CLIENT DEDUPLICATION & CONSOLIDATION
    # -------------------------------------------------------------
    res_clients = await db.execute(select(Client).order_by(Client.id.asc()))
    all_clients = res_clients.scalars().all()

    clients_by_norm: Dict[str, List[Client]] = {}
    for cl in all_clients:
        norm_k = normalize_name(cl.name)
        if not norm_k:
            continue
        clients_by_norm.setdefault(norm_k, []).append(cl)

    merged_clients_count = 0
    client_merge_details = []

    for norm_k, cl_list in clients_by_norm.items():
        if len(cl_list) <= 1:
            continue

        # Choose canonical client: the one with the lowest ID, or the most complete metadata
        canonical = cl_list[0]
        duplicate_ids = [c.id for c in cl_list[1:]]

        # Consolidate metadata into canonical client
        for dup in cl_list[1:]:
            if not canonical.dob and dup.dob:
                canonical.dob = dup.dob
            if not canonical.phone and dup.phone:
                canonical.phone = dup.phone
            if not canonical.email and dup.email:
                canonical.email = dup.email
            if (not canonical.address or canonical.address == "Corpus Christi, TX") and dup.address and dup.address != "Corpus Christi, TX":
                canonical.address = dup.address
            if dup.notes and (not canonical.notes or dup.notes not in canonical.notes):
                if not canonical.notes:
                    canonical.notes = dup.notes
                else:
                    canonical.notes += f" | {dup.notes}"

        # Re-link all Cases pointing to duplicate client IDs
        await db.execute(
            update(Case)
            .where(Case.client_id.in_(duplicate_ids))
            .values(client_id=canonical.id)
        )

        # Re-link all Documents pointing to duplicate client IDs
        await db.execute(
            update(Document)
            .where(Document.client_id.in_(duplicate_ids))
            .values(client_id=canonical.id)
        )

        # Delete duplicate client rows
        await db.execute(
            delete(Client).where(Client.id.in_(duplicate_ids))
        )

        merged_clients_count += len(duplicate_ids)
        client_merge_details.append({
            "client_name": canonical.name,
            "canonical_id": canonical.id,
            "merged_ids": duplicate_ids,
        })

    await db.flush()

    # -------------------------------------------------------------
    # 2. CASE DEDUPLICATION & CONSOLIDATION
    # -------------------------------------------------------------
    res_cases = await db.execute(select(Case).order_by(Case.id.asc()))
    all_cases = res_cases.scalars().all()

    cases_by_norm: Dict[str, List[Case]] = {}
    for cs in all_cases:
        if not cs.case_number:
            continue
        norm_cs = normalize_case_number(cs.case_number)
        cases_by_norm.setdefault(norm_cs, []).append(cs)

    merged_cases_count = 0
    case_merge_details = []

    for norm_cs, cs_list in cases_by_norm.items():
        if len(cs_list) <= 1:
            continue

        canonical_cs = cs_list[0]
        duplicate_case_ids = [c.id for c in cs_list[1:]]

        # Consolidate Case metadata
        for dup_cs in cs_list[1:]:
            if not canonical_cs.client_id and dup_cs.client_id:
                canonical_cs.client_id = dup_cs.client_id
            if dup_cs.has_appointment_order:
                canonical_cs.has_appointment_order = True
            if dup_cs.has_appointment_acceptance:
                canonical_cs.has_appointment_acceptance = True
            if dup_cs.appointment_status in ("CONFIRMED_AND_ACCEPTED", "AWAITING_ACCEPTANCE", "VERIFIED_ON_DOCKET"):
                canonical_cs.appointment_status = dup_cs.appointment_status
            if dup_cs.appointment_order_date and not canonical_cs.appointment_order_date:
                canonical_cs.appointment_order_date = dup_cs.appointment_order_date
            if dup_cs.acceptance_filed_date and not canonical_cs.acceptance_filed_date:
                canonical_cs.acceptance_filed_date = dup_cs.acceptance_filed_date
            if dup_cs.client_contact_date and not canonical_cs.client_contact_date:
                canonical_cs.client_contact_date = dup_cs.client_contact_date
            if dup_cs.charge_description and (not canonical_cs.charge_description or canonical_cs.charge_description == "Class A/B Misdemeanor"):
                canonical_cs.charge_description = dup_cs.charge_description
            if dup_cs.bond_amount and not canonical_cs.bond_amount:
                canonical_cs.bond_amount = dup_cs.bond_amount
                canonical_cs.bond_type = dup_cs.bond_type

        # Re-link Documents
        await db.execute(
            update(Document)
            .where(Document.case_id.in_(duplicate_case_ids))
            .values(case_id=canonical_cs.id)
        )

        # Re-link Events
        await db.execute(
            update(Event)
            .where(Event.case_id.in_(duplicate_case_ids))
            .values(case_id=canonical_cs.id)
        )

        # Re-link Vouchers
        await db.execute(
            update(Voucher)
            .where(Voucher.case_id.in_(duplicate_case_ids))
            .values(case_id=canonical_cs.id)
        )

        # Re-link Time Entries
        await db.execute(
            update(TimeEntry)
            .where(TimeEntry.case_id.in_(duplicate_case_ids))
            .values(case_id=canonical_cs.id)
        )

        # Delete duplicate case rows
        await db.execute(
            delete(Case).where(Case.id.in_(duplicate_case_ids))
        )

        merged_cases_count += len(duplicate_case_ids)
        case_merge_details.append({
            "case_number": canonical_cs.case_number,
            "canonical_id": canonical_cs.id,
            "merged_ids": duplicate_case_ids,
        })

    # -------------------------------------------------------------
    # 3. VOUCHER DEDUPLICATION (Consolidate identical historical vouchers)
    # -------------------------------------------------------------
    res_vchs = await db.execute(select(Voucher).order_by(Voucher.id.asc()))
    all_vchs = res_vchs.scalars().all()
    vchs_by_key: Dict[str, List[Voucher]] = {}
    for v in all_vchs:
        v_key = f"{v.case_id}_{v.voucher_number or ''}_{v.amount_requested}"
        vchs_by_key.setdefault(v_key, []).append(v)

    merged_vouchers_count = 0
    for v_key, v_list in vchs_by_key.items():
        if len(v_list) > 1:
            canonical_vch = v_list[0]
            dup_vch_ids = [v.id for v in v_list[1:]]
            # Re-link time entries to the canonical voucher before removing duplicates
            await db.execute(
                update(TimeEntry)
                .where(TimeEntry.voucher_id.in_(dup_vch_ids))
                .values(voucher_id=canonical_vch.id)
            )
            await db.execute(delete(Voucher).where(Voucher.id.in_(dup_vch_ids)))
            merged_vouchers_count += len(dup_vch_ids)

    await db.commit()

    return {
        "success": True,
        "merged_clients_count": merged_clients_count,
        "merged_cases_count": merged_cases_count,
        "merged_vouchers_count": merged_vouchers_count,
        "client_merge_details": client_merge_details,
        "case_merge_details": case_merge_details,
        "message": f"Deduplication complete: {merged_clients_count} duplicate client(s) and {merged_cases_count} duplicate case(s) consolidated into canonical records.",
    }
