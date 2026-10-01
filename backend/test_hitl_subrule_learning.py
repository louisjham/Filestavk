"""
Filestavk - Automated Test Suite for Human-in-the-Loop (HITL) Fallback & Dynamic Sub-Rule Learning Engine
Tests that when a required field cannot be identified:
1. The parser halts and flags needs_human_review=True with explicit missing_fields (no guessing).
2. The human supplies the correct value and teaches a dynamic ExtractionSubRule.
3. The parsing pipeline resumes and completes the Case and Event lifecycle.
4. Future documents matching the pattern are automatically parsed with zero human intervention.
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
from app.models.extraction_sub_rule import ExtractionSubRule
from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES
from app.services.document_extractor_service import (
    extract_legal_entities,
    REQUIRED_FIELDS_BY_DOC_TYPE,
    apply_learned_sub_rules,
)
from app.routers.documents import (
    human_correction_document,
    HumanCorrectionRequest,
    apply_document_rule_to_ingestion,
)
from sqlalchemy import select, delete


async def test_hitl_and_subrule_learning_flow():
    print("\n======================================================================")
    print("=== Step 1: Testing Zero-Hallucination Halting on Missing Fields ===")
    print("======================================================================")

    # Document text with missing court and judge (custom non-standard header)
    unfamiliar_text = """
    CAUSE NO. 2026-CR-8899-Z
    THE STATE OF TEXAS VS. DAVID MARTINEZ
    ORDER OF APPOINTMENT OF COUNSEL
    On this 18th day of September, 2026, the Court finds the defendant is indigent.
    Counsel Kimbel Brandon is hereby appointed to represent the defendant.
    """

    entities = extract_legal_entities(unfamiliar_text, "Order_Appt_Custom.pdf")

    print(f"  Classification: {entities.get('classification_label')}")
    print(f"  Primary Case: {entities.get('primary_case_number')}")
    print(f"  Defendant: {entities.get('defendant_name')}")
    print(f"  Court: {entities.get('court')}")
    print(f"  Needs Human Review: {entities.get('needs_human_review')}")
    print(f"  Missing Fields: {entities.get('missing_fields')}")

    assert entities["classification_label"] == "appointment_order"
    assert entities["primary_case_number"] == "2026-CR-8899-Z"
    assert entities["defendant_name"] == "David Martinez"
    assert entities["court"] is None or entities["court"] == ""
    # Zero hallucination: It must NOT guess 347th District Court or another venue!
    assert entities["needs_human_review"] is True
    assert "court" in entities["missing_fields"]
    print("  [PASS] Parser correctly halted and flagged missing court without guessing.")

    print("\n======================================================================")
    print("=== Step 2: Ingesting Document into DB in AWAITING_HUMAN_REVIEW State ===")
    print("======================================================================")

    async with async_session_maker() as session:
        # Seed default document rules
        for r_dict in DEFAULT_DOCUMENT_RULES:
            existing = await session.execute(
                select(DocumentRule).where(DocumentRule.document_type == r_dict["document_type"])
            )
            if not existing.scalars().first():
                session.add(DocumentRule(**r_dict))
        await session.commit()

        # Clean up any prior test records for David Martinez
        c_res = await session.execute(select(Client).where(Client.name == "David Martinez"))
        for cl in c_res.scalars().all():
            cases_res = await session.execute(select(Case).where(Case.client_id == cl.id))
            for cs in cases_res.scalars().all():
                await session.execute(delete(Event).where(Event.case_id == cs.id))
                await session.execute(delete(Document).where(Document.case_id == cs.id))
                await session.delete(cs)
            await session.delete(cl)
        
        # Clean up any prior subrules for custom test
        await session.execute(delete(ExtractionSubRule).where(ExtractionSubRule.field_name == "court", ExtractionSubRule.pattern_or_value == "117th District Court"))
        await session.commit()

        # Provision client & case
        client = Client(name="David Martinez", phone="361-555-9011")
        session.add(client)
        await session.flush()

        case = Case(
            client_id=client.id,
            case_number="2026-CR-8899-Z",
            court="Pending Venue Verification",
            status="OPEN",
            stage="MAGISTRATE_HEARING",
        )
        session.add(case)
        await session.flush()

        doc = Document(
            case_id=case.id,
            client_id=client.id,
            filename="Order_Appt_Custom.pdf",
            filepath="C:/antigravity/Filestavk/backend/data/documents/Order_Appt_Custom.pdf",
            doc_type="pdf",
            source="upload",
            classification_label=entities["classification_label"],
            classification_confidence=entities["confidence"],
            metadata_json=str({
                "review_status": "AWAITING_HUMAN_REVIEW",
                "missing_fields": entities["missing_fields"],
                "human_review_instructions": entities["human_review_instructions"],
                "legal_metadata": entities,
            }).replace("'", '"'),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        print(f"  Ingested Document ID={doc.id} with status AWAITING_HUMAN_REVIEW.")

        print("\n======================================================================")
        print("=== Step 3: Human Corrects Court & Teaches Reusable ExtractionSubRule ===")
        print("======================================================================")

        correction_req = HumanCorrectionRequest(
            corrections={
                "court": "117th District Court",
                "judge": "Hon. Sandra Watts",
            },
            learn_subrule=True,
            subrule_field="court",
            subrule_pattern="2026-CR-8899-Z", # Anchor pattern to associate with 117th
            subrule_type="CONSTANT_OVERRIDE",
            subrule_doc_type="appointment_order",
        )

        mock_user = {"id": 1, "username": "kimbel", "role": "attorney"}
        res = await human_correction_document(
            id=doc.id,
            req=correction_req,
            db=session,
            current_user=mock_user,
        )

        print(f"  Correction Response Status: {res.get('status')}")
        print(f"  Learned Sub-Rule ID: {res.get('learned_subrule_id')}")

        assert res.get("status") == "APPROVED"
        assert res.get("learned_subrule_id") is not None

        # Verify Document in DB is now APPROVED and Case is updated
        await session.refresh(doc)
        await session.refresh(case)
        print(f"  Case Court in DB: {case.court}")
        print(f"  Case Judge in DB: {case.judge}")

        assert case.court == "117th District Court"
        assert case.judge == "Hon. Sandra Watts"
        print("  [PASS] Human correction applied, Case updated, and SubRule persisted.")

        print("\n======================================================================")
        print("=== Step 4: Testing Automatic Zero-Touch Extraction on Next Document ===")
        print("======================================================================")

        # Query active sub-rules from DB
        subrules_q = await session.execute(select(ExtractionSubRule).where(ExtractionSubRule.is_active == True))
        active_subrules = subrules_q.scalars().all()
        print(f"  Active Learned Sub-Rules in DB: {len(active_subrules)}")
        for sr in active_subrules:
            print(f"    - Field: {sr.field_name} | Type: {sr.rule_type} | Pattern/Value: {sr.pattern_or_value} | DocType: {sr.document_type}")

        # Ingest a second document matching the learned anchor
        second_doc_text = """
        CAUSE NO. 2026-CR-8899-Z
        THE STATE OF TEXAS VS. DAVID MARTINEZ
        ORDER OF APPOINTMENT OF COUNSEL
        On this 19th day of September, 2026, indigent defendant is appointed Kimbel Brandon.
        """

        auto_entities = extract_legal_entities(
            second_doc_text,
            "Order_Appt_Second_Time.pdf",
            sub_rules=active_subrules,
        )

        print(f"  Second Doc Classification: {auto_entities.get('classification_label')}")
        print(f"  Second Doc Court: {auto_entities.get('court')}")
        print(f"  Second Doc Needs Human Review: {auto_entities.get('needs_human_review')}")
        print(f"  Second Doc Missing Fields: {auto_entities.get('missing_fields')}")

        # Assert zero human review needed!
        assert auto_entities["court"] == "117th District Court"
        assert auto_entities["needs_human_review"] is False
        assert len(auto_entities["missing_fields"]) == 0
        print("  [PASS] Second document parsed 100% automatically using learned sub-rule!")


def main():
    print("======================================================================")
    print("  HUMAN-IN-THE-LOOP & DYNAMIC EXTRACTION SUB-RULE LEARNING TEST SUITE ")
    print("======================================================================")
    asyncio.run(test_hitl_and_subrule_learning_flow())
    print("\n======================================================================")
    print("  ALL HITL SUB-RULE LEARNING TESTS PASSED WITH 100% SUCCESS! ")
    print("======================================================================")


if __name__ == "__main__":
    main()
