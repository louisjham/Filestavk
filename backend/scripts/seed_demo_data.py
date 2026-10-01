"""
Seed Demo Database for Filestavk.
Populates backend/data/filestavk_demo.db with realistic, non-PII test entities:
- Anonymized clients with (361) 555-01XX numbers and generic Corpus Christi addresses.
- Structured mock cases across multiple courts, judges, and stages.
- $16,650.00 in realistic paid vouchers (14 online, 9 paper) matching dashboard radar.
- Classified demo documents and event-driven document rules.
"""

import os
import sys
import asyncio
from datetime import datetime, timezone

# Ensure backend root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Force demo database configuration
os.environ["FILESTAVK_DEMO"] = "true"

from app.database import engine, Base, async_session_maker
from app.models.client import Client
from app.models.case import Case
from app.models.document import Document
from app.models.event import Event
from app.models.time_entry import Voucher, TimeEntry
from app.models.document_rule import DocumentRule, DEFAULT_DOCUMENT_RULES


async def seed():
    print(f"[DEMO SEEDER] Initializing schema for demo database: {engine.url}")
    async with engine.begin() as conn:
        # Re-create all tables clean
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # 1. Seed Document Rules
        print("[DEMO SEEDER] Seeding Document Rules...")
        for rule_dict in DEFAULT_DOCUMENT_RULES:
            rule = DocumentRule(**rule_dict)
            session.add(rule)
        await session.flush()

        # 2. Seed Anonymized Clients
        print("[DEMO SEEDER] Seeding Anonymized Clients...")
        clients_data = [
            Client(
                name="Alex Morgan",
                dob="04/15/1992",
                address="100 N. Shoreline Blvd, Suite 200, Corpus Christi, TX 78401",
                phone="(361) 555-0142",
                email="alex.morgan@example.com",
                notes="Client intake verified. Signed representation agreement on file.",
            ),
            Client(
                name="Jordan Taylor",
                dob="11/22/1988",
                address="500 N. Water St, Corpus Christi, TX 78401",
                phone="(361) 555-0189",
                email="jordan.taylor@example.com",
                notes="Client in custody. Art. 26.04 48-hour contact requirement satisfied.",
            ),
            Client(
                name="Casey Rivera",
                dob="07/08/1995",
                address="222 S. Staples St, Corpus Christi, TX 78404",
                phone="(361) 555-0177",
                email="casey.rivera@example.com",
                notes="Art. 39.14 discovery audit completed. Missing CAD audio flagged.",
            ),
            Client(
                name="Taylor Brooks",
                dob="01/30/1984",
                address="1200 S. Padre Island Dr, Corpus Christi, TX 78416",
                phone="(361) 555-0123",
                email="taylor.brooks@example.com",
                notes="Bail reduction pending under Art. 17.151 CCP.",
            ),
            Client(
                name="Sam Bennett",
                dob="09/14/1990",
                address="4500 Ocean Dr, Corpus Christi, TX 78412",
                phone="(361) 555-0155",
                email="sam.bennett@example.com",
                notes="Pre-trial conference set in 347th District Court.",
            ),
            Client(
                name="Morgan Smith",
                dob="03/18/1986",
                address="800 Leopard St, Corpus Christi, TX 78401",
                phone="(361) 555-0190",
                email="morgan.smith@example.com",
                notes="Case disposed. Final order entered. Full voucher paid.",
            ),
        ]
        session.add_all(clients_data)
        await session.flush()

        # 3. Seed Realistic Cases
        print("[DEMO SEEDER] Seeding Mock Cases...")
        cases_data = [
            Case(
                client_id=clients_data[0].id,
                case_number="2024-CR-00101-A",
                court="County Court at Law No. 3",
                judge="Hon. Deeanne Galvan",
                case_type="CRIMINAL",
                charge_description="Class A/B Misdemeanor - Driving While Intoxicated",
                status="OPEN",
                stage="PRE_TRIAL",
                is_cja=True,
                in_custody=False,
                has_appointment_order=True,
                has_appointment_acceptance=True,
                appointment_status="CONFIRMED_AND_ACCEPTED",
                voucher_status="UNBILLED",
                notes="Pre-trial waiver submitted. Awaiting docket call setting.",
            ),
            Case(
                client_id=clients_data[1].id,
                case_number="2024-CR-00102-B",
                court="28th District Court",
                judge="Hon. Nanette Hasette",
                case_type="CRIMINAL",
                charge_description="Aggravated Assault with Deadly Weapon (Felony 2)",
                status="OPEN",
                stage="MAGISTRATE_HEARING",
                is_cja=True,
                in_custody=True,
                jail_facility="Nueces County Jail - Main",
                has_appointment_order=True,
                has_appointment_acceptance=False,
                appointment_status="AWAITING_ACCEPTANCE",
                voucher_status="NONE",
                notes="In custody. Awaiting file-stamped Acceptance form.",
            ),
            Case(
                client_id=clients_data[2].id,
                case_number="2024-CR-00103-C",
                court="94th District Court",
                judge="Hon. Bobby Galvan",
                case_type="CRIMINAL",
                charge_description="Engaging in Organized Criminal Activity (Felony 3)",
                status="OPEN",
                stage="DISCOVERY",
                is_cja=True,
                in_custody=False,
                has_appointment_order=True,
                has_appointment_acceptance=True,
                appointment_status="CONFIRMED_AND_ACCEPTED",
                voucher_status="NONE",
                notes="State discovery batch received. Discrepancy analysis active.",
            ),
            Case(
                client_id=clients_data[3].id,
                case_number="2024-CR-00104-D",
                court="105th District Court",
                judge="Hon. Jack W. Pulcher",
                case_type="CRIMINAL",
                charge_description="Assault Family Violence Impeding Breath (Felony 3)",
                status="OPEN",
                stage="MAGISTRATE_HEARING",
                is_cja=True,
                in_custody=True,
                jail_facility="Nueces County Jail - Main",
                has_appointment_order=True,
                has_appointment_acceptance=False,
                appointment_status="AWAITING_ACCEPTANCE",
                voucher_status="NONE",
                notes="Speedy release clock at day 12 of 90.",
            ),
            Case(
                client_id=clients_data[4].id,
                case_number="2024-CR-00105-E",
                court="347th District Court",
                judge="Hon. Missy Medary",
                case_type="CRIMINAL",
                charge_description="Possession CS PG 1/1-B <1G (State Jail Felony)",
                status="OPEN",
                stage="DISCOVERY",
                is_cja=True,
                in_custody=False,
                has_appointment_order=True,
                has_appointment_acceptance=True,
                appointment_status="CONFIRMED_AND_ACCEPTED",
                voucher_status="DRAFT",
                notes="Motion to Suppress warrantless search drafted.",
            ),
            Case(
                client_id=clients_data[5].id,
                case_number="2023-CR-00088-F",
                court="County Court at Law No. 1",
                judge="Hon. Robert J. Vargas",
                case_type="CRIMINAL",
                charge_description="Unlawful Carrying of a Weapon (Class A Misdemeanor)",
                status="DISPOSED",
                stage="DISPOSED",
                disposition_type="DISMISSED",
                is_cja=True,
                in_custody=False,
                has_appointment_order=True,
                has_appointment_acceptance=True,
                appointment_status="CONFIRMED_AND_ACCEPTED",
                voucher_status="PAID",
                notes="Case successfully dismissed. Warrant payment reconciled.",
            ),
        ]
        session.add_all(cases_data)
        await session.flush()

        # 4. Seed Vouchers ($16,650.00 total paid: 14 online, 9 paper)
        print("[DEMO SEEDER] Seeding Vouchers & Financial Radar ($16,650.00 recovered)...")
        vouchers_data = []

        # 1 Draft / Ready to be Filed Voucher
        vouchers_data.append(
            Voucher(
                case_id=cases_data[0].id,
                voucher_number="VCH-2024-00101",
                voucher_type="CJA-MISDEMEANOR",
                status="DRAFT",
                amount_requested=500.00,
                submission_method="ONLINE_PORTAL",
                has_appointment_order_verified=False,
                notes="Initial draft. Waiting on signed order confirmation.",
            )
        )

        # 14 Online Paid Vouchers:
        # 1 x $450 + 13 x $650 = $8,900
        vouchers_data.append(
            Voucher(
                case_id=cases_data[5].id,
                voucher_number="VCH-18020",
                voucher_type="CJA-MISDEMEANOR",
                status="PAID",
                amount_requested=450.00,
                amount_approved=450.00,
                amount_paid=450.00,
                paid_date="2026-09-08",
                submission_method="ONLINE_PORTAL",
                warrant_number="WRT-2026-88412",
                notes="Online submission via Nueces Appointed Attorney Portal.",
            )
        )
        for i in range(1, 14):
            vouchers_data.append(
                Voucher(
                    case_id=cases_data[5].id,
                    voucher_number=f"VCH-2024-{1000 + i}",
                    voucher_type="CJA-FELONY",
                    status="PAID",
                    amount_requested=650.00,
                    amount_approved=650.00,
                    amount_paid=650.00,
                    paid_date="2026-08-15",
                    submission_method="ONLINE_PORTAL",
                    warrant_number=f"WRT-2026-{90000 + i}",
                    notes="Electronic voucher approved and paid.",
                )
            )

        # 9 Paper Paid Vouchers:
        # 1 x $1,200 + 7 x $800 ($5,600) + 1 x $950 = $7,750
        # Total Paid = $8,900 + $7,750 = $16,650.00
        vouchers_data.append(
            Voucher(
                case_id=cases_data[5].id,
                voucher_number="PV-2023-0091",
                voucher_type="CJA-FELONY",
                status="PAID",
                amount_requested=1200.00,
                amount_approved=1200.00,
                amount_paid=1200.00,
                paid_date="2023-12-04",
                submission_method="PAPER_HAND_SUBMITTED",
                warrant_number="WRT-2023-99014",
                notes="Historical paper voucher hand-submitted to Auditor.",
            )
        )
        vouchers_data.append(
            Voucher(
                case_id=cases_data[5].id,
                voucher_number="PV-2024-0015",
                voucher_type="CJA-FELONY",
                status="PAID",
                amount_requested=950.00,
                amount_approved=950.00,
                amount_paid=950.00,
                paid_date="2024-04-10",
                submission_method="PAPER_HAND_SUBMITTED",
                warrant_number="WRT-2024-11405",
                notes="Paper claim approved by District Court.",
            )
        )
        for i in range(1, 8):
            vouchers_data.append(
                Voucher(
                    case_id=cases_data[5].id,
                    voucher_number=f"PV-2024-{100 + i}",
                    voucher_type="CJA-FELONY",
                    status="PAID",
                    amount_requested=800.00,
                    amount_approved=800.00,
                    amount_paid=800.00,
                    paid_date="2024-06-20",
                    submission_method="PAPER_HAND_SUBMITTED",
                    warrant_number=f"WRT-2024-{80000 + i}",
                    notes="Legacy paper claim approved and funded.",
                )
            )

        session.add_all(vouchers_data)
        await session.flush()

        # 5. Seed Documents
        print("[DEMO SEEDER] Seeding Anonymized Demo Documents...")
        now = datetime.now(timezone.utc)
        docs_data = [
            Document(
                case_id=cases_data[0].id,
                client_id=clients_data[0].id,
                filename="Order_Of_Appt-2024CR00101.pdf",
                classification_label="appointment_order",
                classification_confidence=1.0,
                doc_type="pdf",
                source="ingestion_hub",
                ingested_at=now,
            ),
            Document(
                case_id=cases_data[0].id,
                client_id=clients_data[0].id,
                filename="Order_Of_Acceptance-2024CR00101.pdf",
                classification_label="appointment_acceptance",
                classification_confidence=1.0,
                doc_type="pdf",
                source="efile_texas",
                ingested_at=now,
            ),
            Document(
                case_id=cases_data[1].id,
                client_id=clients_data[1].id,
                filename="Offense_Report_2024-00102.pdf",
                classification_label="police_report",
                classification_confidence=1.0,
                doc_type="pdf",
                source="da_portal",
                ingested_at=now,
            ),
            Document(
                case_id=cases_data[0].id,
                client_id=clients_data[0].id,
                filename="Waiver_Of_Arraignment_Sample.pdf",
                classification_label="waiver_of_arraignment",
                classification_confidence=1.0,
                doc_type="pdf",
                source="manual_upload",
                ingested_at=now,
            ),
            Document(
                case_id=cases_data[2].id,
                client_id=clients_data[2].id,
                filename="Discovery_Notice_Production_Batch_1.pdf",
                classification_label="discovery_compliance",
                classification_confidence=0.98,
                doc_type="pdf",
                source="ingestion_hub",
                ingested_at=now,
            ),
        ]
        session.add_all(docs_data)

        # 6. Seed Events
        print("[DEMO SEEDER] Seeding Calendar & Docket Events...")
        events_data = [
            Event(
                case_id=cases_data[0].id,
                event_type="hearing",
                title="Pre-Trial Hearing Setting",
                description="County Court at Law No. 3 - Pre-Trial Conference",
                event_date="2026-09-24 09:00:00",
            ),
            Event(
                case_id=cases_data[1].id,
                event_type="order",
                title="Order Appointing Counsel Entered",
                description="28th District Court appointment order recorded.",
                event_date="2026-09-10 14:00:00",
            ),
            Event(
                case_id=cases_data[2].id,
                event_type="discovery",
                title="State Discovery Tender Logged",
                description="Article 39.14 discovery batch tender uploaded.",
                event_date="2026-09-12 11:30:00",
            ),
        ]
        session.add_all(events_data)

        await session.commit()
        print("[DEMO SEEDER] Successfully populated filestavk_demo.db with complete demo dataset!")


if __name__ == "__main__":
    asyncio.run(seed())
