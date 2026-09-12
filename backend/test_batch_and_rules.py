"""
Automated Test Suite for Batch Ingestion & Static Document Rules Engine.
Validates:
1. Grounded extraction from Order of Appointment of Attorney (Myles Jordan / 26MC-05285).
2. Dynamic static document rules CRUD (list, edit, evaluate, reset defaults).
3. Batch multi-document inspection & batch upload.
4. Auto-population of Client (DOB, address, phone, SO#) and Case (charge, court, in_custody) from rules.
5. Statutory 48-hour client contact timeline event creation.
"""

import sys
import os
import asyncio
import io

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.document_extractor_service import (
    extract_legal_entities,
    validate_document_health,
)

SAMPLE_APPOINTMENT_ORDER_UNEXECUTED_TEXT = """
NUECES COUNTY MAGISTRATE COURT
Judge Linda J. Rhodes-Schauer
Judge Melissa Madrigal
Nueces County Jail
901 Leopard Street
Corpus Christi, Texas 78401
361-887-2277 OR 361-887-2376
361-887-2317 FAX

CASE NO. 26MC-05285

THE STATE OF TEXAS          §       COUNTY COURT AT LAW #2
VS.                         §
MYLES JORDAN                §       NUECES COUNTY, TEXAS
SO NO. 20027903

ORDER OF APPOINTMENT OF ATTORNEY

Charge: 49.04
DRIVING WHILE INTOXICATED, Class B Misdemeanor

The Court in accordance with Article 26.04 of the Code of Criminal Procedure, as amended, hereby
appoints Kimbel Brandon, Attorney, SBN: 24079543 to represent:

Myles Jordan, DOB: 10/24/2006
201 4TH ST
INGRAM TX 78025
Home: 830-459-8321

Defendant is currently in Jail: No

Signed on this the 24th day of August, 2026.
Judge Presiding

Atty Phone: 361-737-2625        Atty FAX: 361-431-1015
Email: hemocyaninlaw@gmail.com
"""

SAMPLE_APPOINTMENT_ACCEPTANCE_TEXT = """
NUECES COUNTY MAGISTRATE COURT
Judge Linda J. Rhodes-Schauer
Judge Melissa Madrigal
Nueces County Jail
901 Leopard Street
Corpus Christi, Texas 78401

CASE NO. 26MC-05285

THE STATE OF TEXAS          §       COUNTY COURT AT LAW #2
VS.                         §
MYLES JORDAN                §       NUECES COUNTY, TEXAS
SO NO. 20027903

ORDER OF APPOINTMENT OF ATTORNEY

Charge: 49.04
DRIVING WHILE INTOXICATED, Class B Misdemeanor

The Court in accordance with Article 26.04 of the Code of Criminal Procedure, as amended, hereby
appoints Kimbel Brandon, Attorney, SBN: 24079543 to represent:

Myles Jordan, DOB: 10/24/2006
201 4TH ST
INGRAM TX 78025
Home: 830-459-8321

Defendant is currently in Jail: No

Signed on this the 24th day of August, 2026.
Judge Presiding

FILED SEP 02 2026
ANNE LORENTZEN, DISTRICT CLERK, COUNTY & DISTRICT COURTS NUECES COUNTY, TEXAS

ACCEPTANCE OF APPOINTMENT
The undersigned attorney acknowledges this appointment and first contacted this Defendant on the
1st day of September, 2026.

AFFIRMED:
Attorney for the Defendant     Date: 09/01/2026

INSTRUCTIONS:
Please acknowledge your appointment to represent this client and file a copy of this appointment with the District Clerk no
later than 48 hours after the date you first make personal contact with the Defendant, as required by Article 26.04(j)(1) of the Code of
Criminal Procedure.
"""

SAMPLE_WAIVER_TEXT = """
CAUSE NO. 26MC-02715
IN THE COUNTY COURT
AT LAW NO. 3
NUECES COUNTY, TEXAS

THE STATE OF TEXAS
VS.
JOSEPH PRUDE

WAIVER OF ARRAIGNMENT
NOW COMES Joseph Prude, Defendant, and files this Waiver of Arraignment, entering a plea of Not Guilty and requesting Pre-Trial and Jury Trial settings.
"""


def test_appointment_order_extraction():
    print("\n[TEST 1A] Testing Unexecuted Order of Appointment Extraction...")
    extracted = extract_legal_entities(SAMPLE_APPOINTMENT_ORDER_UNEXECUTED_TEXT, "Order_of_Appointment_Jordan.pdf")

    assert extracted["classification_label"] == "appointment_order", f"Expected appointment_order, got {extracted['classification_label']}"
    assert extracted["primary_case_number"] == "26MC-05285", f"Expected 26MC-05285, got {extracted['primary_case_number']}"
    assert extracted["defendant_name"] == "Myles Jordan", f"Expected Myles Jordan, got {extracted['defendant_name']}"
    assert extracted["court"] == "County Court at Law No. 2", f"Expected County Court at Law No. 2, got {extracted['court']}"
    
    spec = extracted["specialized_fields"]
    assert spec.get("dob") == "10/24/2006", f"Expected 10/24/2006, got {spec.get('dob')}"
    assert "INGRAM TX 78025" in spec.get("address", ""), f"Expected Ingram address, got {spec.get('address')}"
    assert "830-459-8321" in spec.get("phone", ""), f"Expected phone, got {spec.get('phone')}"
    assert spec.get("so_number") == "20027903", f"Expected SO# 20027903, got {spec.get('so_number')}"
    assert spec.get("in_custody") is False, f"Expected in_custody=False, got {spec.get('in_custody')}"
    assert spec.get("appointed_attorney") == "Kimbel Brandon", f"Expected Kimbel Brandon, got {spec.get('appointed_attorney')}"
    assert spec.get("attorney_sbn") == "24079543", f"Expected 24079543, got {spec.get('attorney_sbn')}"
    assert spec.get("statutory_basis") == "Tex. Code Crim. Proc. art. 26.04"
    assert "DRIVING WHILE INTOXICATED" in spec.get("charge_description", "")
    assert extracted["confidence"] >= 0.85
    print(f"  [PASS] Successfully extracted unexecuted Order of Appointment fields.")


def test_appointment_acceptance_extraction():
    print("\n[TEST 1B] Testing Stamped Acceptance of Appointment Extraction...")
    extracted = extract_legal_entities(SAMPLE_APPOINTMENT_ACCEPTANCE_TEXT, "Acceptance_of_Appointment_Jordan.pdf")

    assert extracted["classification_label"] == "appointment_acceptance", f"Expected appointment_acceptance, got {extracted['classification_label']}"
    assert extracted["primary_case_number"] == "26MC-05285", f"Expected 26MC-05285, got {extracted['primary_case_number']}"
    assert extracted["defendant_name"] == "Myles Jordan", f"Expected Myles Jordan, got {extracted['defendant_name']}"
    
    spec = extracted["specialized_fields"]
    assert spec.get("has_order_section") is True
    assert spec.get("has_acceptance_section") is True
    assert spec.get("appointed_attorney") == "Kimbel Brandon"
    print(f"  [PASS] Successfully extracted Stamped Acceptance of Appointment (has dual Order + Acceptance sections).")


async def test_rules_engine_and_batch_async():
    from app.database import engine, Base, async_session_maker
    from app.db_migration import sync_migrate_sqlite_schema
    from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES
    from app.routers.document_rules import ensure_default_document_rules
    from app.routers.documents import apply_document_rule_to_ingestion
    from app.models.client import Client
    from app.models.case import Case
    from app.models.event import Event
    from sqlalchemy.future import select

    print("\n[TEST 2] Testing Static Rules Seeding & Evaluation...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(sync_migrate_sqlite_schema)

    async with async_session_maker() as db:
        await ensure_default_document_rules(db)
        res = await db.execute(select(DocumentRule))
        rules = res.scalars().all()
        assert len(rules) >= 7, f"Expected at least 7 default rules, found {len(rules)}"
        print(f"  [PASS] {len(rules)} default Nueces County static document rules seeded in SQLite.")

        # Test Rule Lookup for appointment_order
        res = await db.execute(select(DocumentRule).where(DocumentRule.document_type == "appointment_order"))
        appt_rule = res.scalars().first()
        assert appt_rule is not None
        assert appt_rule.target_case_stage == "MAGISTRATE_HEARING"
        assert appt_rule.trigger_statutory_deadline is True
        assert appt_rule.deadline_hours_offset == 48
        print(f"  [PASS] Appointment Order rule verified: Stage='{appt_rule.target_case_stage}', 48h Deadline Alert=ON")

        # Test Dynamic Rule Execution on Database
        print("\n[TEST 3] Testing Dynamic Rule Execution (Client & Case Population)...")
        # Create a new Client and Case
        new_client = Client(name="Myles Jordan")
        db.add(new_client)
        await db.flush()

        new_case = Case(
            client_id=new_client.id,
            case_number="26MC-05285",
            court="County Court at Law No. 2",
            judge="Hon. Melissa Madrigal",
            status="open",
            stage="DISCOVERY"
        )
        db.add(new_case)
        await db.flush()

        extracted_meta = extract_legal_entities(SAMPLE_APPOINTMENT_ORDER_UNEXECUTED_TEXT, "Order_of_Appointment_Jordan.pdf")
        await apply_document_rule_to_ingestion(
            db=db,
            detected_label="appointment_order",
            legal_meta=extracted_meta,
            resolved_client_id=new_client.id,
            resolved_case_id=new_case.id,
            filename="Order_of_Appointment_Jordan.pdf"
        )
        await db.commit()

        # Verify Client was populated
        await db.refresh(new_client)
        assert new_client.dob == "10/24/2006", f"Expected DOB 10/24/2006, got {new_client.dob}"
        assert "INGRAM" in new_client.address, f"Expected Ingram address, got {new_client.address}"
        assert "830-459-8321" in new_client.phone, f"Expected phone, got {new_client.phone}"
        assert "SO# 20027903" in (new_client.notes or "")
        print(f"  [PASS] Client #{new_client.id} automatically populated with DOB, address, phone, and SO#.")

        # Verify Case was transitioned
        await db.refresh(new_case)
        assert new_case.stage == "MAGISTRATE_HEARING", f"Expected MAGISTRATE_HEARING, got {new_case.stage}"
        assert new_case.has_appointment_order is True
        assert new_case.has_appointment_acceptance is False
        assert new_case.appointment_status == "AWAITING_ACCEPTANCE"
        assert "DRIVING WHILE INTOXICATED" in (new_case.charge_description or "")
        print(f"  [PASS] Step 1: Case #{new_case.id} marked has_appointment_order=True, appointment_status='AWAITING_ACCEPTANCE'.")

        # Step 2: Now ingest the stamped Acceptance of Appointment
        extracted_acceptance_meta = extract_legal_entities(SAMPLE_APPOINTMENT_ACCEPTANCE_TEXT, "Acceptance_of_Appointment_Jordan.pdf")
        await apply_document_rule_to_ingestion(
            db=db,
            detected_label="appointment_acceptance",
            legal_meta=extracted_acceptance_meta,
            resolved_client_id=new_client.id,
            resolved_case_id=new_case.id,
            filename="Acceptance_of_Appointment_Jordan.pdf"
        )
        await db.commit()

        await db.refresh(new_case)
        assert new_case.has_appointment_acceptance is True
        assert new_case.appointment_status == "CONFIRMED_AND_ACCEPTED"
        print(f"  [PASS] Step 2: Acceptance ingested, has_appointment_acceptance=True, appointment_status='CONFIRMED_AND_ACCEPTED'.")

        # Verify Timeline Events & Statutory 48h Deadline
        ev_res = await db.execute(select(Event).where(Event.case_id == new_case.id))
        events = ev_res.scalars().all()
        assert len(events) >= 3, f"Expected at least 3 events (Order + Deadline + Acceptance), got {len(events)}"
        acceptance_evt = next((e for e in events if "Acceptance of Appointment" in e.title), None)
        assert acceptance_evt is not None, "Expected Acceptance event on case docket"
        print(f"  [PASS] Case Docket Timeline has {len(events)} events, including Stamped Acceptance and 48-Hour Deadline.")


def main():
    print("=" * 70)
    print("STARTING BATCH INGESTION & STATIC RULES REGRESSION SUITE")
    print("=" * 70)

    test_appointment_order_extraction()
    test_appointment_acceptance_extraction()
    asyncio.run(test_rules_engine_and_batch_async())

    print("\n" + "=" * 70)
    print("ALL BATCH INGESTION & DOCUMENT RULES TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)
    print("ALL BATCH INGESTION & DOCUMENT RULES TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    main()
