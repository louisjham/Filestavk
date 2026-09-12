"""
End-to-End Automated Test for Order of Acceptance Ingestion, Mid-Stride Resolution & Voucher Pipeline.
"""

import os
import io
import asyncio
from datetime import datetime, timezone
from fastapi import UploadFile
from sqlalchemy.future import select
from sqlalchemy import func

from app.database import async_session_maker
from app.models.case import Case
from app.models.client import Client
from app.models.document import Document
from app.models.event import Event
from app.models.time_entry import Voucher
from app.routers.documents import upload_document, approve_document_review
from app.routers.settings import get_dashboard_morning_alerts
from app.routers.vouchers import get_vouchers, get_voucher_stats


async def main():
    print("=== Testing End-to-End Order of Acceptance Ingestion Workflow ===")

    pdf_path = "C:/antigravity/Filestavk/Acceptance of Appointment-26MC-02456.pdf"
    assert os.path.exists(pdf_path), f"File not found: {pdf_path}"

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="Acceptance of Appointment-26MC-02456.pdf",
        headers={"content-type": "application/pdf"}
    )

    async with async_session_maker() as db:
        # Check if case already exists, delete test data if so to test mid-stride fresh provisioning
        existing_c = await db.execute(select(Case).where(Case.case_number == "26MC-02456"))
        c_obj = existing_c.scalars().first()
        if c_obj:
            print(f"Cleaning up previous test run for Case #{c_obj.case_number} (ID: {c_obj.id})...")
            # Delete related events, documents, vouchers
            v_res = await db.execute(select(Voucher).where(Voucher.case_id == c_obj.id))
            for v in v_res.scalars().all():
                await db.delete(v)
            d_res = await db.execute(select(Document).where(Document.case_id == c_obj.id))
            for d in d_res.scalars().all():
                await db.delete(d)
            e_res = await db.execute(select(Event).where(Event.case_id == c_obj.id))
            for e in e_res.scalars().all():
                await db.delete(e)
            cl_id = c_obj.client_id
            await db.delete(c_obj)
            if cl_id:
                cl_res = await db.execute(select(Client).where(Client.id == cl_id))
                cl_obj = cl_res.scalars().first()
                if cl_obj:
                    await db.delete(cl_obj)
            await db.commit()

        # Ingest document via upload_document
        print("\n--- Ingesting 'Acceptance of Appointment-26MC-02456.pdf' ---")
        current_user = {"username": "kimbel", "role": "attorney"}
        doc = await upload_document(file=upload_file, db=db, current_user=current_user)

        assert doc is not None
        assert doc.id is not None
        print(f"  [PASS] Document Ingested: ID={doc.id}, Filename={doc.filename}")

        # Verify renaming standard: Order_Of_Acceptance-<CaseNumber>.pdf
        expected_filename = "Order_Of_Acceptance-26MC-02456.pdf"
        assert doc.filename == expected_filename, f"Expected {expected_filename}, got {doc.filename}"
        assert os.path.exists(doc.filepath), f"File does not exist at {doc.filepath}"
        assert expected_filename in doc.filepath
        print(f"  [PASS] Standardized Renaming Verified: Saved as '{doc.filename}' at '{doc.filepath}'")

        # Verify Client Auto-Provisioning
        client_res = await db.execute(select(Client).where(Client.id == doc.client_id))
        client = client_res.scalars().first()
        assert client is not None
        assert "oscar perez" in client.name.lower()
        assert client.dob == "03/08/1977"
        assert client.phone == "(361) 737-2625"
        assert "8318 POCONO" in client.address
        print(f"  [PASS] Client Provisioned: Name='{client.name}', DOB={client.dob}, Phone={client.phone}, Address='{client.address}'")

        # Verify Mid-Stride Case Provisioning
        case_res = await db.execute(select(Case).where(Case.id == doc.case_id))
        case = case_res.scalars().first()
        assert case is not None
        assert case.case_number == "26MC-02456"
        assert case.has_appointment_acceptance is True, "has_appointment_acceptance must be True"
        assert case.has_appointment_order is False, "has_appointment_order must be False (mid-stride)"
        assert case.appointment_status == "CONFIRMED_AND_ACCEPTED"
        assert case.voucher_status == "READY_TO_FILE"
        assert case.in_custody is True
        assert case.client_contact_date == "09/01/2026"
        print(f"  [PASS] Mid-Stride Case Provisioned: #{case.case_number}, has_acceptance={case.has_appointment_acceptance}, has_order={case.has_appointment_order}, appt_status={case.appointment_status}, voucher_status={case.voucher_status}, in_custody={case.in_custody}")

        # Verify Docket Events
        events_res = await db.execute(select(Event).where(Event.case_id == case.id))
        events = events_res.scalars().all()
        event_types = [e.event_type for e in events]
        assert "MID_STRIDE_MISSING_ORDER" in event_types, f"Expected MID_STRIDE_MISSING_ORDER in {event_types}"
        assert "APPOINTMENT_ACCEPTANCE" in event_types, f"Expected APPOINTMENT_ACCEPTANCE in {event_types}"
        print(f"  [PASS] Events Recorded on Docket: {event_types}")

        # Verify Voucher Created in READY_TO_FILE
        vch_res = await db.execute(select(Voucher).where(Voucher.case_id == case.id))
        voucher = vch_res.scalars().first()
        assert voucher is not None
        assert voucher.status == "READY_TO_FILE"
        assert voucher.has_appointment_order_verified is True
        print(f"  [PASS] Voucher Pipeline Transitioned: Number={voucher.voucher_number}, Status={voucher.status}, Amount=${voucher.amount_requested}")

        # Verify Dashboard Alerts
        briefing = await get_dashboard_morning_alerts(db=db, current_user=current_user)
        alert_types = [a["type"] for a in briefing["alerts"]]
        assert "MID_STRIDE_MISSING_ORDER" in alert_types, f"Expected MID_STRIDE_MISSING_ORDER in dashboard alerts: {alert_types}"
        assert "VOUCHER_READY_TO_FILE" in alert_types, f"Expected VOUCHER_READY_TO_FILE in dashboard alerts: {alert_types}"
        print(f"  [PASS] Dashboard Alerts Triggered: MID_STRIDE_MISSING_ORDER and VOUCHER_READY_TO_FILE active.")

        # Verify Voucher Stats & Aging
        stats = await get_voucher_stats(db=db, current_user=current_user)
        assert stats["ready_to_file_count"] >= 1
        print(f"  [PASS] Voucher Stats: ready_to_file_count={stats['ready_to_file_count']}")

        # Test Human Review Approval Endpoint
        print("\n--- Testing Human Review Approval Endpoint (POST /documents/{id}/approve-review) ---")
        import json
        review_doc = Document(
            case_id=case.id,
            client_id=client.id,
            filename="Unverified_Acceptance.pdf",
            filepath=doc.filepath,
            doc_type="pdf",
            source="upload",
            classification_label="appointment_acceptance",
            classification_confidence=0.5,
            metadata_json=json.dumps({
                "review_status": "AWAITING_HUMAN_REVIEW",
                "human_review_instructions": "Verify clerk stamp and attorney signature",
                "has_clerk_file_stamp": False,
                "has_attorney_affirmation": False,
            })
        )
        db.add(review_doc)
        await db.commit()
        await db.refresh(review_doc)

        approve_res = await approve_document_review(id=review_doc.id, db=db, current_user=current_user)
        assert approve_res["status"] == "APPROVED"
        refreshed_meta = json.loads(review_doc.metadata_json)
        assert refreshed_meta["review_status"] == "APPROVED"
        assert refreshed_meta["reviewed_by"] == "kimbel"
        print(f"  [PASS] approve_document_review successfully approved review_status='APPROVED' for document {review_doc.id}")

    print("\n======================================================================")
    print("ALL ACCEPTANCE WORKFLOW INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(main())
