"""
Automated unit & regression test for Michael Morton Act (Art. 39.14 CCP) Discovery Gap Auditor.
"""

import asyncio
import os
import json
from app.database import async_session_maker
from app.models.case import Case
from app.models.client import Client
from app.models.document import Document
from app.services.discovery_audit_service import discovery_audit_service
from sqlalchemy import select


async def main():
    print("=== Step 1: Setting Up Mock Case & Evidentiary Narrative ===")
    async with async_session_maker() as db:
        # Create test client
        test_client = Client(
            name="Ramiro Gutierrez",
            dob="05/14/1988",
            phone="(361) 555-0199",
            address="4202 Ocean Dr, Corpus Christi, TX 78411",
            notes="Test client for discovery audit"
        )
        db.add(test_client)
        await db.flush()

        # Create test case with in-custody booking
        test_case = Case(
            client_id=test_client.id,
            case_number="2026-CR-9999-D",
            court="105th District Court",
            judge="Hon. Jack W. Pulcher",
            case_type="CRIMINAL",
            charge_description="Possession of Controlled Substance PG 1 <1G (State Jail Felony)",
            status="OPEN",
            stage="DISCOVERY",
            is_cja=True,
            in_custody=True,
            jail_booking_date="2026-05-10",
        )
        db.add(test_case)
        await db.flush()

        # Add Offense Report Document with rich narrative tokens
        narrative_body = """
        CORPUS CHRISTI POLICE DEPARTMENT INCIDENT REPORT
        INCIDENT NO: CCPD-26-08192
        LOCATION: 1200 S Port Ave, Corpus Christi, TX
        DATE/TIME: August 14, 2026 22:45

        NARRATIVE:
        Officer J. Rodriguez #1842 responded to a 911 call reporting a suspicious vehicle.
        Upon arrival, Officer Rodriguez activated Axon BWC 4 and made contact with the driver.
        Officer observed defendant nervous. Officer searched the trunk of the vehicle and seized
        a clear plastic baggie containing white powdery residue. The evidence was packaged into
        evidence locker 12 and submitted to DPS Crime Lab for chemical analysis.

        Officer handcuffed the defendant and placed him in the back of patrol unit 14 where
        the officer asked him about the baggie. Defendant admitted he bought it downtown.
        Defendant was booked into Nueces County Jail.
        """

        report_doc = Document(
            case_id=test_case.id,
            client_id=test_client.id,
            filename="CCPD_Offense_Report_26-08192.pdf",
            filepath="/data/documents/test/CCPD_Offense_Report_26-08192.pdf",
            doc_type="police_report",
            classification_label="police_report",
            content_text=narrative_body,
        )
        db.add(report_doc)
        await db.commit()

        case_id = test_case.id
        client_id = test_client.id

    print("\n=== Step 2: Executing Discovery Gap Audit ===")
    async with async_session_maker() as db:
        report = await discovery_audit_service.audit_case_discovery(db, case_id)

        assert report["case_number"] == "2026-CR-9999-D"
        assert report["defendant_name"] == "Ramiro Gutierrez"
        summary = report["summary"]
        print(f"  [PASS] Summary: Total Mentioned={summary['total_items_mentioned']}, Missing={summary['missing_count']}, Suppression={summary['suppression_flags_count']}")

        # Verify Missing Evidence Gaps (BWC, 911 call, DPS Lab)
        missing_cats = [m["category"] for m in report["missing_evidence"]]
        assert "BWC_FOOTAGE" in missing_cats, "Expected BWC_FOOTAGE in missing items"
        assert "CAD_911_AUDIO" in missing_cats, "Expected CAD_911_AUDIO in missing items"
        assert "FORENSIC_LAB_REPORT" in missing_cats, "Expected FORENSIC_LAB_REPORT in missing items"
        print(f"  [PASS] Missing Evidence Detected: {missing_cats}")

        # Verify Suppression Flags (Art. 38.22 custodial statement, Art. 38.23 warrantless search, Art. 17.151 clock)
        suppression_ids = [s["id"] for s in report["suppression_flags"]]
        assert "suppress_38_22" in suppression_ids, "Expected Art. 38.22 suppression flag"
        assert "suppress_38_23" in suppression_ids, "Expected Art. 38.23 warrantless search suppression flag"
        assert "art_17_151_clock" in suppression_ids, "Expected Art. 17.151 in-custody clock flag"
        print(f"  [PASS] Suppression Triggers Flagged: {suppression_ids}")

        print("\n=== Step 3: Generating Art. 39.14 Motion to Compel ===")
        motion = discovery_audit_service.generate_motion_to_compel(report)
        assert "CAUSE NO. 2026-CR-9999-D" in motion
        assert "105TH DISTRICT COURT" in motion
        assert "RAMIRO GUTIERREZ" in motion
        assert "Watkins v. State, 619 S.W.3d 265" in motion
        assert "Kimbel Brandon" in motion
        assert "24079543" in motion
        assert "HEMOCYANIN LAW" in motion.upper()
        assert "Body-Worn Camera Footage" in motion
        assert "DPS Forensic Crime Lab Report" in motion
        print("  [PASS] Motion to Compel successfully formatted with Texas statutory authority and Kimbel's signature block!")

        # Cleanup test records
        c_obj = await db.get(Case, case_id)
        if c_obj:
            d_res = await db.execute(select(Document).where(Document.case_id == case_id))
            for d in d_res.scalars().all():
                await db.delete(d)
            await db.delete(c_obj)
        cl_obj = await db.get(Client, client_id)
        if cl_obj:
            await db.delete(cl_obj)
        await db.commit()
        print("\n=== All Discovery Audit Tests Passed Successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())
