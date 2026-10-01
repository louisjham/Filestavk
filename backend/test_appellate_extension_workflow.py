"""
Filestavk - Comprehensive Texas Appellate Extension Workflow Test Suite
Tests ingestion, parsing, timeline scheduling, dashboard alerting,
and drafting for 13th Court of Appeals brief extension motions and orders.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend package is in python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database import async_session_maker, engine
from app.models.client import Client
from app.models.case import Case
from app.models.document import Document
from app.models.event import Event
from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES
from app.services.document_extractor_service import (
    validate_document_health,
    extract_content,
    extract_legal_entities
)
from app.routers.documents import apply_document_rule_to_ingestion
from app.routers.settings import get_dashboard_morning_alerts
from app.routers.cases import get_appellate_extension_draft
from sqlalchemy import select, delete


TEMPLATES_DIR = Path(r"C:\antigravity\Filestavk\templates")

DOCX_FIRST_MOTION = TEMPLATES_DIR / "Motion to Extend Time Appeal .docx"
PDF_FIRST_MOTION = TEMPLATES_DIR / "Motion to Extend Time Appeal .pdf"
PDF_GRANT_ORDER = TEMPLATES_DIR / "13-26-00155-CR_MT EXT BRIEF DISP__GRANT__FILECOPY.pdf"
PDF_SECOND_MOTION = TEMPLATES_DIR / "Motion to Extend Time Appeal second.pdf"


def test_template_extractions():
    print("\n=======================================================")
    print("=== Step 1: Testing Entity Extraction on Template Files ===")
    print("=======================================================")

    # 1. First Motion DOCX
    print(f"\n--- Testing First Motion DOCX: {DOCX_FIRST_MOTION.name} ---")
    assert DOCX_FIRST_MOTION.exists(), f"File missing: {DOCX_FIRST_MOTION}"
    with open(DOCX_FIRST_MOTION, "rb") as f:
        bytes_docx = f.read()
    health_docx = validate_document_health(bytes_docx, DOCX_FIRST_MOTION.name)
    assert health_docx["is_healthy"], f"DOCX health check failed: {health_docx}"
    content_docx = extract_content(str(DOCX_FIRST_MOTION), DOCX_FIRST_MOTION.name)
    entities_docx = extract_legal_entities(content_docx["text"], DOCX_FIRST_MOTION.name)

    print(f"  Classification: {entities_docx.get('classification_label')} (Confidence: {entities_docx.get('confidence')})")
    print(f"  Defendant Name: {entities_docx.get('defendant_name')}")
    print(f"  Appellate Case: {entities_docx.get('appellate_case_number')}")
    print(f"  Motion Sequence: {entities_docx.get('specialized_fields', {}).get('motion_sequence')}")
    print(f"  Requested Due Date: {entities_docx.get('specialized_fields', {}).get('requested_due_date')} (ISO: {entities_docx.get('specialized_fields', {}).get('extended_due_date_iso')})")
    print(f"  Opposing Counsel: {entities_docx.get('specialized_fields', {}).get('opposing_counsel_status')}")

    assert entities_docx["classification_label"] == "appellate_motion_extension"
    assert "Frank" in entities_docx["defendant_name"] and "Roberts" in entities_docx["defendant_name"]
    assert entities_docx["appellate_case_number"] == "13-26-00155-CR"
    assert entities_docx["specialized_fields"]["motion_sequence"] == "First"
    assert entities_docx["specialized_fields"]["extension_count"] == 1
    assert entities_docx["specialized_fields"]["opposing_counsel_status"] == "Unopposed"
    print("  [PASS] First Motion DOCX Extraction Verified.")

    # 2. First Motion PDF
    print(f"\n--- Testing First Motion PDF: {PDF_FIRST_MOTION.name} ---")
    assert PDF_FIRST_MOTION.exists(), f"File missing: {PDF_FIRST_MOTION}"
    with open(PDF_FIRST_MOTION, "rb") as f:
        bytes_pdf = f.read()
    health_pdf = validate_document_health(bytes_pdf, PDF_FIRST_MOTION.name)
    assert health_pdf["is_healthy"], f"PDF health check failed: {health_pdf}"
    content_pdf = extract_content(str(PDF_FIRST_MOTION), PDF_FIRST_MOTION.name)
    entities_pdf = extract_legal_entities(content_pdf["text"], PDF_FIRST_MOTION.name)

    print(f"  Classification: {entities_pdf.get('classification_label')}")
    print(f"  Defendant: {entities_pdf.get('defendant_name')}")
    print(f"  Appellate Case: {entities_pdf.get('appellate_case_number')}")
    print(f"  Good Cause Summary: {entities_pdf.get('specialized_fields', {}).get('good_cause_summary')}")

    assert entities_pdf["classification_label"] == "appellate_motion_extension"
    assert entities_pdf["appellate_case_number"] == "13-26-00155-CR"
    assert "fmla" in entities_pdf["specialized_fields"]["good_cause_statement"].lower() or "medical" in entities_pdf["specialized_fields"]["good_cause_statement"].lower()
    print("  [PASS] First Motion PDF Extraction Verified.")

    # 3. Court of Appeals Disposition Grant Order PDF
    print(f"\n--- Testing Disposition Grant Order PDF: {PDF_GRANT_ORDER.name} ---")
    assert PDF_GRANT_ORDER.exists(), f"File missing: {PDF_GRANT_ORDER}"
    with open(PDF_GRANT_ORDER, "rb") as f:
        bytes_grant = f.read()
    health_grant = validate_document_health(bytes_grant, PDF_GRANT_ORDER.name)
    assert health_grant["is_healthy"], f"Grant Order health check failed: {health_grant}"
    content_grant = extract_content(str(PDF_GRANT_ORDER), PDF_GRANT_ORDER.name)
    entities_grant = extract_legal_entities(content_grant["text"], PDF_GRANT_ORDER.name)

    print(f"  Classification: {entities_grant.get('classification_label')}")
    print(f"  Disposition: {entities_grant.get('specialized_fields', {}).get('disposition')}")
    print(f"  Appellate Case: {entities_grant.get('appellate_case_number')}")
    print(f"  Trial Court Case: {entities_grant.get('specialized_fields', {}).get('trial_court_case_number')}")
    print(f"  Extended Due Date: {entities_grant.get('specialized_fields', {}).get('extended_due_date')} (ISO: {entities_grant.get('specialized_fields', {}).get('extended_due_date_iso')})")
    print(f"  Order Date: {entities_grant.get('specialized_fields', {}).get('order_date')} (ISO: {entities_grant.get('specialized_fields', {}).get('order_date_iso')})")

    assert entities_grant["classification_label"] == "appellate_order_granting_extension"
    assert entities_grant["specialized_fields"]["disposition"] == "GRANTED"
    assert entities_grant["appellate_case_number"] == "13-26-00155-CR"
    assert entities_grant["specialized_fields"]["trial_court_case_number"] == "24FC-2874E"
    assert entities_grant["specialized_fields"]["extended_due_date_iso"] == "2026-09-14"
    assert entities_grant["specialized_fields"]["order_date_iso"] == "2026-09-03"
    print("  [PASS] Disposition Grant Order Extraction Verified.")

    # 4. Second Motion PDF
    print(f"\n--- Testing Second Motion PDF: {PDF_SECOND_MOTION.name} ---")
    assert PDF_SECOND_MOTION.exists(), f"File missing: {PDF_SECOND_MOTION}"
    with open(PDF_SECOND_MOTION, "rb") as f:
        bytes_second = f.read()
    health_second = validate_document_health(bytes_second, PDF_SECOND_MOTION.name)
    assert health_second["is_healthy"], f"Second Motion health check failed: {health_second}"
    content_second = extract_content(str(PDF_SECOND_MOTION), PDF_SECOND_MOTION.name)
    entities_second = extract_legal_entities(content_second["text"], PDF_SECOND_MOTION.name)

    print(f"  Classification: {entities_second.get('classification_label')}")
    print(f"  Motion Sequence: {entities_second.get('specialized_fields', {}).get('motion_sequence')}")
    print(f"  Extension Count: {entities_second.get('specialized_fields', {}).get('extension_count')}")
    print(f"  Prior Due Date: {entities_second.get('specialized_fields', {}).get('current_due_date')} (ISO: {entities_second.get('specialized_fields', {}).get('current_due_date_iso')})")
    print(f"  Requested Due Date: {entities_second.get('specialized_fields', {}).get('requested_due_date')} (ISO: {entities_second.get('specialized_fields', {}).get('extended_due_date_iso')})")

    assert entities_second["classification_label"] == "appellate_motion_extension"
    assert entities_second["specialized_fields"]["motion_sequence"] == "Second"
    assert entities_second["specialized_fields"]["extension_count"] == 2
    assert entities_second["specialized_fields"]["current_due_date_iso"] == "2026-09-14"
    assert entities_second["specialized_fields"]["extended_due_date_iso"] == "2026-10-14"
    print("  [PASS] Second Motion PDF Extraction Verified.")


async def test_end_to_end_appellate_pipeline():
    print("\n=======================================================")
    print("=== Step 2: Testing Full Ingestion & Rule Pipeline ===")
    print("=======================================================")

    async with async_session_maker() as session:
        # Ensure default document rules exist
        for r_dict in DEFAULT_DOCUMENT_RULES:
            existing = await session.execute(
                select(DocumentRule).where(DocumentRule.document_type == r_dict["document_type"])
            )
            rule = existing.scalars().first()
            if not rule:
                new_r = DocumentRule(**r_dict)
                session.add(new_r)
        await session.commit()

        # Clean up any prior test records for Frank Roberts
        c_res = await session.execute(select(Client).where(Client.name.ilike("%Frank%Roberts%")))
        clients = c_res.scalars().all()
        for c in clients:
            cases_res = await session.execute(select(Case).where(Case.client_id == c.id))
            for cs in cases_res.scalars().all():
                await session.execute(delete(Event).where(Event.case_id == cs.id))
                await session.execute(delete(Document).where(Document.case_id == cs.id))
                await session.delete(cs)
            await session.delete(c)
        await session.commit()

        # 1. Provision initial Trial Court case for Frank Roberts (24FC-2874E)
        print("\n--- Provisioning Initial Trial Court Case (24FC-2874E) ---")
        client = Client(
            name="Frank A. Roberts",
            phone="361-555-0199",
            email="frank.roberts@example.com"
        )
        session.add(client)
        await session.flush()

        case = Case(
            client_id=client.id,
            case_number="24FC-2874E",
            trial_court_case_number="24FC-2874E",
            court="105th District Court",
            judge="Hon. Jack W. Pulcher",
            case_type="FELONY",
            charge_description="Aggravated Assault with a Deadly Weapon",
            status="OPEN",
            stage="PRE_TRIAL"
        )
        session.add(case)
        await session.commit()
        await session.refresh(case)
        print(f"  Created Trial Case ID={case.id}, Number={case.case_number}, Client={client.name}")

        # 2. Ingest Grant Order (PDF_GRANT_ORDER)
        print("\n--- Ingesting 13th Court of Appeals Grant Order ---")
        content_grant = extract_content(str(PDF_GRANT_ORDER), PDF_GRANT_ORDER.name)
        entities_grant = extract_legal_entities(content_grant["text"], PDF_GRANT_ORDER.name)

        doc_grant = Document(
            case_id=case.id,
            client_id=client.id,
            filename=PDF_GRANT_ORDER.name,
            filepath=str(PDF_GRANT_ORDER),
            doc_type="pdf",
            source="upload",
            classification_label=entities_grant["classification_label"],
            classification_confidence=entities_grant.get("confidence", 0.95),
            metadata_json=str(entities_grant["specialized_fields"])
        )
        session.add(doc_grant)
        await session.flush()

        # Apply rule
        await apply_document_rule_to_ingestion(
            session,
            entities_grant["classification_label"],
            entities_grant,
            client.id,
            case.id,
            PDF_GRANT_ORDER.name
        )
        await session.commit()
        await session.refresh(case)

        print(f"  Updated Case Stage: {case.stage}")
        print(f"  Appellate Case Number: {case.appellate_case_number}")
        print(f"  Appellate Court: {case.appellate_court}")
        print(f"  Appellate Brief Due Date: {case.appellate_brief_due_date}")
        print(f"  Appellate Motion Status: {case.appellate_motion_status}")

        assert case.stage == "APPEAL"
        assert case.appellate_case_number == "13-26-00155-CR"
        assert "13th Court of Appeals" in case.appellate_court
        assert str(case.appellate_brief_due_date) == "2026-09-14"
        assert case.appellate_motion_status in ["GRANTED", "EXTENSION_GRANTED"]

        # Check Timeline Events
        events_res = await session.execute(select(Event).where(Event.case_id == case.id))
        events = events_res.scalars().all()
        print(f"  Generated {len(events)} Timeline Events:")
        for ev in events:
            print(f"    - [{ev.event_type}] ({ev.event_date}) {ev.title}: {ev.description}")
        
        event_types = [ev.event_type for ev in events]
        assert any("order" in ev.event_type.lower() or "granted" in ev.title.lower() for ev in events)
        assert any("brief" in ev.title.lower() or "deadline" in ev.event_type.lower() for ev in events)
        print("  [PASS] Grant Order Ingestion & Case Linking Verified.")

        # 3. Test Dashboard Alert Calculation
        print("\n--- Testing Appellate Deadline Dashboard Alerts ---")
        mock_user = {"id": 1, "username": "kimbel", "role": "attorney"}
        alerts = await get_dashboard_morning_alerts(db=session, current_user=mock_user)
        appellate_alerts = [a for a in alerts.get("alerts", []) if "Appellate Brief" in a.get("title", "") or "13-26-00155-CR" in a.get("title", "") or "Roberts" in a.get("description", "")]
        print(f"  Found {len(appellate_alerts)} Appellate Alerts:")
        for a in appellate_alerts:
            print(f"    - Severity: [{a.get('severity')}] | Title: {a.get('title')} | Action: {a.get('recommended_action')}")
        
        assert len(appellate_alerts) > 0, "Expected at least one appellate alert for due date 2026-09-14"
        print("  [PASS] Dashboard Alert Generation Verified.")

        # 4. Ingest Second Motion (PDF_SECOND_MOTION)
        print("\n--- Ingesting Second Motion for Extension (Pushes deadline to 2026-10-14) ---")
        content_second = extract_content(str(PDF_SECOND_MOTION), PDF_SECOND_MOTION.name)
        entities_second = extract_legal_entities(content_second["text"], PDF_SECOND_MOTION.name)

        doc_second = Document(
            case_id=case.id,
            client_id=client.id,
            filename=PDF_SECOND_MOTION.name,
            filepath=str(PDF_SECOND_MOTION),
            doc_type="pdf",
            source="upload",
            classification_label=entities_second["classification_label"],
            classification_confidence=entities_second.get("confidence", 0.95),
            metadata_json=str(entities_second["specialized_fields"])
        )
        session.add(doc_second)
        await session.flush()

        await apply_document_rule_to_ingestion(
            session,
            entities_second["classification_label"],
            entities_second,
            client.id,
            case.id,
            PDF_SECOND_MOTION.name
        )
        await session.commit()
        await session.refresh(case)

        print(f"  Case Appellate Extension Count: {case.appellate_extension_count}")
        print(f"  Case Appellate Motion Status: {case.appellate_motion_status}")
        print(f"  Case Appellate Brief Due Date: {case.appellate_brief_due_date}")
        print(f"  Case Good Cause: {case.appellate_extension_reason}")

        assert case.appellate_extension_count == 2
        assert case.appellate_motion_status in ["PENDING", "MOTION_PENDING"]
        assert str(case.appellate_brief_due_date) == "2026-09-14"
        assert "medical" in case.appellate_extension_reason.lower() or "fmla" in case.appellate_extension_reason.lower() or "justice" in case.appellate_extension_reason.lower()

        # Check requested deadline event
        events_m_res = await session.execute(select(Event).where(Event.case_id == case.id))
        all_events = events_m_res.scalars().all()
        assert any(ev.event_date == "2026-10-14" for ev in all_events), "Expected requested deadline event for 2026-10-14"
        print("  [PASS] Second Motion Ingestion & Case State Update Verified.")

        # 5. Test 1-Click Texas 13th COA Pleading Generator
        print("\n--- Testing 1-Click Texas 13th Court of Appeals Pleading Generator ---")
        draft = await get_appellate_extension_draft(case.id, db=session, current_user=mock_user)
        print(f"  Sequence: {draft.get('motion_sequence')}")
        print(f"  Appellate Case: {draft.get('appellate_case_number')}")
        print(f"  Trial Case: {draft.get('trial_court_case_number')}")
        print(f"  Prior Due Date: {draft.get('prior_due_date')}")
        print(f"  Requested Due Date: {draft.get('requested_due_date')}")
        print("\n--- Snippet of Generated Motion Text ---")
        snippet = "\n".join(draft.get("draft_pleading_text", "").split("\n")[:25])
        print(snippet)
        print("...")

        assert draft.get("motion_sequence") == "THIRD"  # Next motion after Second is Third
        assert draft.get("appellate_case_number") == "13-26-00155-CR"
        assert "13TH SUPREME JUDICIAL DISTRICT OF TEXAS" in draft.get("draft_pleading_text", "")
        assert "COURT OF APPEALS" in draft.get("draft_pleading_text", "")
        assert "Kimbel Brandon" in draft.get("draft_pleading_text", "")
        assert "State Bar No. 24079543" in draft.get("draft_pleading_text", "")
        assert "CERTIFICATE OF CONFERENCE" in draft.get("draft_pleading_text", "")
        assert "CERTIFICATE OF SERVICE" in draft.get("draft_pleading_text", "")
        print("  [PASS] 1-Click 13th Court of Appeals Pleading Generator Verified.")


def main():
    print("======================================================================")
    print(" TEXAS 13TH COURT OF APPEALS EXTENSION OF TIME AUTOMATION TEST SUITE ")
    print("======================================================================")
    test_template_extractions()
    asyncio.run(test_end_to_end_appellate_pipeline())
    print("\n======================================================================")
    print(" ALL APPELLATE EXTENSION AUTOMATION TESTS PASSED WITH 100% SUCCESS! ")
    print("======================================================================")


if __name__ == "__main__":
    main()
