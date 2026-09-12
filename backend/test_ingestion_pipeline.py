"""
Integration test for Email Connector, RFC 822 Staging, ETL Parser, and Human Verification Pipeline.
"""

import asyncio
import os
import json
from app.database import engine, async_session_maker, Base
import app.models
from app.services.email_connector import fetch_live_headers, download_raw_eml
from app.services.email_etl_service import parse_eml_file
from app.models.classification import RawEmailStaging
from app.models.case import Case
from app.models.time_entry import Voucher
from app.models.event import Event
from app.models.document import Document
from sqlalchemy.future import select

async def run_tests():
    print("=== Step 1: Initializing Database Schema ===")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database schema initialized with raw_email_staging table.")

    print("\n=== Step 2: Fetch Live Headers ===")
    headers = fetch_live_headers(limit=10)
    print(f"[OK] Fetched {len(headers)} email headers.")
    for h in headers[:3]:
        print(f"  - Subject: {h['subject'][:60]}... | Tag: {h['filter_tag']} | Cases: {h['extracted_case_numbers']}")

    print("\n=== Step 3: Stage Raw RFC 822 .eml to Semi-Permanent Storage ===")
    sample_id = "sample-103"  # Auditor Warrant Remittance advice
    download_res = download_raw_eml(sample_id)
    assert download_res["success"], "Download raw .eml failed"
    file_path = download_res["file_path"]
    assert os.path.exists(file_path), f"File {file_path} was not created"
    print(f"[OK] Raw .eml saved to {file_path} ({download_res['size_bytes']} bytes).")

    print("\n=== Step 4: Run ETL Parser on Staged RFC 822 .eml ===")
    parsed = parse_eml_file(file_path)
    extracted = parsed.get("extracted", {})
    print(f"  - Extracted Category: {extracted.get('category')}")
    print(f"  - Extracted Case: {extracted.get('primary_case_number')}")
    print(f"  - Presiding Court: {extracted.get('court')}")
    print(f"  - Warrant Number: {extracted.get('specialized_fields', {}).get('warrant_number')}")
    print(f"  - Amount Paid: ${extracted.get('specialized_fields', {}).get('amount_paid')}")
    print(f"  - Confidence: {extracted.get('confidence')}")
    assert extracted.get("category") == "COUNTY_AUDITOR_WARRANT"
    assert extracted.get("primary_case_number") == "2024-CR-3102-E"
    print("[OK] ETL Parser correctly extracted Nueces County legal entities and auditor voucher details.")

    print("\n=== Step 5: Test Staging Table & Human Verification Flow ===")
    async with async_session_maker() as session:
        # Create staging row
        staged_row = RawEmailStaging(
            message_id=sample_id,
            sender=parsed["from"],
            recipient=parsed["to"],
            subject=parsed["subject"],
            date_sent=parsed["date"],
            file_path=file_path,
            raw_size_bytes=download_res["size_bytes"],
            filter_tag=extracted["category"],
            etl_status="PARSED",
            extracted_data_json=json.dumps(extracted),
        )
        session.add(staged_row)
        await session.commit()
        await session.refresh(staged_row)
        print(f"[OK] Staged record created with ID {staged_row.id} and status '{staged_row.etl_status}'.")

        # Simulate Human Verification & Commit
        staged_row.etl_status = "VERIFIED_COMMITTED"
        staged_row.verified_by = "Kimbel Brandon, Esq."
        await session.commit()
        print(f"[OK] Staged record verified and committed by {staged_row.verified_by}.")

    print("\n>>> ALL INGESTION PIPELINE TESTS PASSED! <<<")

if __name__ == "__main__":
    asyncio.run(run_tests())
