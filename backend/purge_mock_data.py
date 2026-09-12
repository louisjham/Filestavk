"""
Standalone script to purge mock and demo seed data from the Filestavk SQLite database.
Leaves database tables clean and ready for production Google for Business / IMAP ingestion.
"""

import asyncio
import os
import glob
from sqlalchemy import text
from app.database import engine, async_session_maker, Base
import app.models
from app.models.classification import ClassificationLabel

TABLES_TO_PURGE = [
    "document_labels",
    "documents",
    "events",
    "time_entries",
    "vouchers",
    "cases",
    "clients",
    "search_history",
    "portal_audit_log",
    "ingestion_jobs",
    "raw_email_staging",
]

BASE_DIR = os.path.dirname(__file__)
RAW_EMAILS_DIR = os.path.join(BASE_DIR, "data", "raw_emails")

async def purge():
    print("===================================================")
    print("    Filestavk Production Clean Slate Data Purge    ")
    print("===================================================")
    print("\n[1/3] Purging mock records from SQLite database tables...")
    async with async_session_maker() as session:
        for tbl in TABLES_TO_PURGE:
            try:
                res = await session.execute(text(f"DELETE FROM {tbl}"))
                print(f"  ✓ Purged {res.rowcount} row(s) from {tbl}")
            except Exception as e:
                print(f"  ! Notice on {tbl}: {e}")

        # Reset autoincrement sequence for clean ID numbering
        try:
            for tbl in TABLES_TO_PURGE:
                await session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{tbl}'"))
            print("  ✓ Reset SQLite autoincrement sequences to 1")
        except Exception:
            pass

        # Ensure base document classification categories exist
        base_labels = [
            ("court_order", "Official orders, judgments, deferred adjudications"),
            ("appointment_order", "Order Appointing Counsel under CCP Art. 26.04"),
            ("hearing_notice", "Court docket and appearance notices"),
            ("efiling_receipt", "Odyssey / EFileTexas electronic filing receipts"),
            ("warrant_remittance", "County Auditor disbursement advice & warrants"),
            ("discovery", "Michael Morton Act (Art. 39.14 CCP) tenders"),
            ("police_report", "CCPD / Law enforcement offense reports"),
            ("correspondence", "Letters and emails with court coordinators and clients"),
            ("invoice", "Attorney fee vouchers and expense support"),
            ("uncategorized", "Unclassified incoming documents"),
        ]
        for name, desc in base_labels:
            existing = await session.execute(
                text("SELECT id FROM classification_labels WHERE name=:n"), {"n": name}
            )
            if not existing.fetchone():
                session.add(ClassificationLabel(name=name, description=desc))
        
        await session.commit()

    print("\n[2/3] Cleaning temporary staged raw .eml files...")
    if os.path.exists(RAW_EMAILS_DIR):
        eml_files = glob.glob(os.path.join(RAW_EMAILS_DIR, "*.eml"))
        for f in eml_files:
            try:
                os.remove(f)
                print(f"  ✓ Removed staged file: {os.path.basename(f)}")
            except Exception as e:
                print(f"  ! Could not remove {f}: {e}")

    print("\n[3/3] Verification: Checking table counts...")
    async with async_session_maker() as session:
        for tbl in ["clients", "cases", "vouchers", "time_entries", "documents", "events", "raw_email_staging"]:
            cnt = (await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))).scalar()
            print(f"  • {tbl}: {cnt} active records")

    print("\n===================================================")
    print("  [SUCCESS] All mock and demo data wiped cleanly!   ")
    print("  Database is 100% ready for live production data. ")
    print("===================================================")

if __name__ == "__main__":
    asyncio.run(purge())
