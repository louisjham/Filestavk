import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.future import select
from app.database import engine, async_session_maker, Base
import app.models
from app.models.client import Client
from app.models.case import Case
from app.models.document import Document
from app.models.event import Event
from app.models.time_entry import TimeEntry, Voucher
from app.models.classification import ClassificationLabel, SearchHistory, PortalAuditLog

async def seed():
    # 1. Recreate tables cleanly
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # --- 1. Clients ---
        c1 = Client(name="Carlos Ramirez", dob="1994-08-12", address="3410 Ayers St, Corpus Christi, TX", phone="(361) 555-0182", email="carlos.ramirez94@gmail.com", notes="Primary contact prefers Spanish/English bilingual text messages.")
        c2 = Client(name="Elena Trevino", dob="1988-11-04", address="5820 Everhart Rd, Corpus Christi, TX", phone="(361) 555-0194", email="elena.trevino@outlook.com", notes="Retained case. Employed with local refinery contractor.")
        c3 = Client(name="Marcus Hernandez", dob="2001-03-22", address="1204 Morgan Ave, Corpus Christi, TX", phone="(361) 555-0129", email="marcus.h01@yahoo.com", notes="Appointed CJA. In custody at Nueces County Jail. Mother (Rosa) often calls.")
        c4 = Client(name="David Garcia", dob="1981-06-15", address="4902 Leopard St, Corpus Christi, TX", phone="(361) 555-0144", email="dgarcia_cc@gmail.com", notes="Completed plea agreement. On 4 years straight probation.")
        c5 = Client(name="Sophia Benavides", dob="1997-09-30", address="2102 Gollihar Rd, Corpus Christi, TX", phone="(361) 555-0177", email="sophia.benavides@gmail.com", notes="Case fully closed and voucher paid.")
        c6 = Client(name="Brandon Miller", dob="1999-12-05", address="714 Lipan St, Corpus Christi, TX", phone="(361) 555-0163", email="brandon.m99@gmail.com", notes="In custody at Nueces County Jail - McConnell Unit. CJA appointed.")
        session.add_all([c1, c2, c3, c4, c5, c6])
        await session.commit()
        for cl in [c1, c2, c3, c4, c5, c6]:
            await session.refresh(cl)

        # --- 2. Cases ---
        now = datetime.now(timezone.utc).date()
        
        # Case 1: Ramirez - Disposed, Unbilled Backlog ($1,250 claimable cash)
        morton_1 = json.dumps({"offense_report": True, "dashcam_video": True, "bodycam_video": True, "dps_lab_report": True, "call_911_audio": False, "brady_notice": True})
        case1 = Case(
            client_id=c1.id,
            case_number="2024-CR-1042-D",
            court="105th District Court",
            judge="Hon. Jack W. Pulcher",
            case_type="CRIMINAL",
            charge_description="POSS CS PG 1/1-B <1G (State Jail Felony)",
            status="DISPOSED",
            stage="DISPOSED",
            is_cja=True,
            in_custody=False,
            voucher_status="UNBILLED",
            has_appointment_order=True,
            appointment_order_date="2024-03-20",
            appointment_status="VERIFIED_ON_DOCKET",
            disposition_type="DISMISSED",
            disposition_date=(now - timedelta(days=45)).strftime("%Y-%m-%d"),
            bond_amount=10000.0,
            bond_type="SURETY",
            bond_conditions="Weekly urinalysis, drug patch, no firearms, travel restricted to Nueces County",
            morton_discovery_json=morton_1,
            opened_date="2024-03-15",
            closed_date=(now - timedelta(days=45)).strftime("%Y-%m-%d"),
            notes="Case dismissed for insufficient evidence. Order Appointing Counsel verified on docket. Ready for online voucher submission ($1,250.00).",
        )

        # Case 2: Trevino - Pre-Trial Retained DWI 3rd
        morton_2 = json.dumps({"offense_report": True, "dashcam_video": True, "bodycam_video": False, "dps_lab_report": False, "call_911_audio": True, "brady_notice": False})
        case2 = Case(
            client_id=c2.id,
            case_number="2024-CR-2180-C",
            court="94th District Court",
            judge="Hon. Bobby Galvan",
            case_type="CRIMINAL",
            charge_description="DRIVING WHILE INTOXICATED 3RD OR MORE (3rd Degree Felony)",
            status="OPEN",
            stage="DISCOVERY",
            is_cja=False,
            in_custody=False,
            voucher_status="NONE",
            has_appointment_order=False,
            appointment_status="RETAINED",
            disposition_type="PENDING",
            bond_amount=25000.0,
            bond_type="PR_BOND",
            bond_conditions="Smart Start ignition interlock on vehicle, SCRAM continuous alcohol monitor, travel permitted to Nueces/San Patricio/Aransas",
            morton_discovery_json=morton_2,
            opened_date="2024-05-10",
            notes="Awaiting DPS Blood Alcohol Lab Analysis and in-car Dashcam from Corpus Christi PD.",
        )

        # Case 3: Hernandez - Aggravated Assault, IN CUSTODY (48 days in jail) & Missing Appointment Order Alert
        morton_3 = json.dumps({"offense_report": True, "dashcam_video": True, "bodycam_video": True, "dps_lab_report": True, "call_911_audio": True, "brady_notice": True})
        case3 = Case(
            client_id=c3.id,
            case_number="2023-CR-4819-A",
            court="28th District Court",
            judge="Hon. Nanette Hasette",
            case_type="CRIMINAL",
            charge_description="AGGRAVATED ASSAULT W/ DEADLY WEAPON (2nd Degree Felony)",
            status="OPEN",
            stage="PRE_TRIAL",
            is_cja=True,
            in_custody=True,
            has_appointment_order=False,
            appointment_status="MISSING_ORDER",
            disposition_type="PENDING",
            jail_booking_date=(now - timedelta(days=48)).strftime("%Y-%m-%d"),
            jail_facility="Nueces County Jail - Main",
            voucher_status="RETURNED",
            bond_amount=50000.0,
            bond_type="SURETY",
            bond_conditions="No contact with complaining witness, GPS ankle monitoring upon release",
            morton_discovery_json=morton_3,
            opened_date="2023-11-02",
            notes="Currently detained in Nueces County Jail. Voucher was returned by Court Coordinator: missing Order Appointing Counsel on docket. Need to call coordinator Melissa.",
        )

        # Case 4: Garcia - Firearm by Felon, Voucher Approved awaiting County Auditor
        morton_4 = json.dumps({"offense_report": True, "dashcam_video": True, "bodycam_video": True, "dps_lab_report": True, "call_911_audio": False, "brady_notice": True})
        case4 = Case(
            client_id=c4.id,
            case_number="2024-CR-3102-E",
            court="214th District Court",
            judge="Hon. Inna Klein",
            case_type="CRIMINAL",
            charge_description="UNLAWFUL POSSESSION OF FIREARM BY FELON (3rd Degree Felony)",
            status="DISPOSED",
            stage="PROBATION",
            is_cja=True,
            in_custody=False,
            voucher_status="APPROVED",
            has_appointment_order=True,
            appointment_order_date="2024-02-22",
            appointment_status="VERIFIED_ON_DOCKET",
            disposition_type="PLEA_GUILTY",
            disposition_date="2024-07-20",
            bond_amount=35000.0,
            bond_type="SURETY",
            bond_conditions="No weapons, report monthly to adult probation",
            morton_discovery_json=morton_4,
            opened_date="2024-02-18",
            closed_date="2024-07-20",
            notes="Plea completed. Voucher approved by Judge Klein, in County Auditor disbursement queue.",
        )

        # Case 5: Benavides - Historical Legacy Paper Voucher Paid
        case5 = Case(
            client_id=c5.id,
            case_number="2023-CR-1109-B",
            court="148th District Court",
            judge="Hon. Carlos Valdez",
            case_type="CRIMINAL",
            charge_description="EVADING ARREST DETENTION W/ VEHICLE (3rd Degree Felony)",
            status="CLOSED",
            stage="DISPOSED",
            is_cja=True,
            in_custody=False,
            voucher_status="PAID",
            has_appointment_order=True,
            appointment_order_date="2023-08-20",
            appointment_status="VERIFIED_ON_DOCKET",
            disposition_type="DISMISSED",
            disposition_date="2024-01-10",
            bond_amount=15000.0,
            bond_type="SURETY",
            opened_date="2023-08-14",
            closed_date="2024-01-10",
            notes="Historical case originally submitted by hand / paper voucher. Warrant #904812 received via direct deposit.",
        )

        # Case 6: Miller - Burglary, IN CUSTODY (62 days in jail awaiting Grand Jury)
        morton_6 = json.dumps({"offense_report": True, "dashcam_video": False, "bodycam_video": True, "dps_lab_report": False, "call_911_audio": True, "brady_notice": False})
        case6 = Case(
            client_id=c6.id,
            case_number="2024-CR-0891-B",
            court="319th District Court",
            judge="Hon. David Stith",
            case_type="CRIMINAL",
            charge_description="BURGLARY OF HABITATION (2nd Degree Felony)",
            status="OPEN",
            stage="INDICTMENT",
            is_cja=True,
            in_custody=True,
            has_appointment_order=True,
            appointment_order_date="2024-06-28",
            appointment_status="VERIFIED_ON_DOCKET",
            disposition_type="PENDING",
            jail_booking_date=(now - timedelta(days=62)).strftime("%Y-%m-%d"),
            jail_facility="Nueces County Jail - McConnell Unit",
            voucher_status="NONE",
            bond_amount=75000.0,
            bond_type="SURETY",
            bond_conditions="Cannot make $75,000 surety bond. Eligible for Art. 17.151 CCP bail reduction hearing (60+ days without indictment).",
            morton_discovery_json=morton_6,
            opened_date="2024-06-25",
            notes="62 days detained in Nueces County Jail without felony indictment. Priority for bond reduction motion.",
        )

        session.add_all([case1, case2, case3, case4, case5, case6])
        await session.commit()
        for cs in [case1, case2, case3, case4, case5, case6]:
            await session.refresh(cs)

        # --- 3. Vouchers ---
        # Voucher 1 (Ramirez) - Unbilled Backlog (Disposed 45 days ago, claimable!)
        disp_1 = (now - timedelta(days=45)).strftime("%Y-%m-%d")
        v1 = Voucher(
            case_id=case1.id,
            voucher_number="VCH-2024-1042",
            voucher_type="CJA-FELONY",
            submission_method="ONLINE_PORTAL",
            status="UNBILLED",
            has_appointment_order_verified=True,
            amount_requested=1250.0,
            disposition_date=disp_1,
            notes="Unbilled backlog from dismissal on 105th District docket. Appointment order verified on docket. Ready to bill.",
        )

        # Voucher 2 (Hernandez) - RETURNED (Missing Appointment Order)
        v2 = Voucher(
            case_id=case3.id,
            voucher_number="VCH-2023-4819",
            voucher_type="CJA-FELONY",
            submission_method="ONLINE_PORTAL",
            status="RETURNED",
            has_appointment_order_verified=False,
            amount_requested=2450.0,
            submitted_date=(now - timedelta(days=12)).strftime("%Y-%m-%d"),
            rejection_reason="Missing Order Appointing Counsel on Odyssey docket. Please contact 28th District Court Coordinator.",
            notes="Returned by 28th District Court Coordinator. Need appointment order entered before resubmitting.",
        )

        # Voucher 3 (Garcia) - APPROVED by Judge (Awaiting Auditor ~14 days)
        v3 = Voucher(
            case_id=case4.id,
            voucher_number="VCH-2024-3102",
            voucher_type="CJA-FELONY",
            submission_method="ONLINE_PORTAL",
            status="APPROVED",
            has_appointment_order_verified=True,
            amount_requested=2100.0,
            amount_approved=2100.0,
            submitted_date=(now - timedelta(days=28)).strftime("%Y-%m-%d"),
            approved_date=(now - timedelta(days=14)).strftime("%Y-%m-%d"),
            notes="Approved by Judge Inna Klein ($2,100.00). In auditor queue for warrant disbursement.",
        )

        # Voucher 4 (Benavides) - PAID via Historical Paper Hand Submission
        v4 = Voucher(
            case_id=case5.id,
            voucher_number="VCH-LEGACY-2023-1109",
            voucher_type="CJA-FELONY",
            submission_method="PAPER_HAND_SUBMITTED",
            status="PAID",
            has_appointment_order_verified=True,
            amount_requested=1650.0,
            amount_approved=1650.0,
            amount_paid=1650.0,
            submitted_date="2024-01-18",
            approved_date="2024-01-26",
            paid_date="2024-02-14",
            warrant_number="WARR-904812",
            notes="Legacy paper voucher submitted by hand to 148th District Court. Paid via Direct Deposit.",
        )

        # Voucher 5 (Interim Draft)
        v5 = Voucher(
            case_id=case3.id,
            voucher_number="VCH-2023-4820-EXP",
            voucher_type="EXPENSE-INVESTIGATOR",
            submission_method="ONLINE_PORTAL",
            status="DRAFT",
            has_appointment_order_verified=False,
            amount_requested=800.0,
            notes="Interim investigator fee voucher draft.",
        )

        session.add_all([v1, v2, v3, v4, v5])
        await session.commit()

        # --- 4. Time Entries ---
        t1 = TimeEntry(case_id=case1.id, service_code="IN_COURT", description="Arraignment & Docket Call (105th District)", hours=2.5, rate=100.0, entry_date="2024-04-10")
        t2 = TimeEntry(case_id=case1.id, service_code="JAIL_VISIT", description="Client conference at Nueces County Jail", hours=2.0, rate=100.0, entry_date="2024-05-12")
        t3 = TimeEntry(case_id=case1.id, service_code="DISCOVERY_REVIEW", description="Reviewed CCP 39.14 offense reports & bodycam", hours=4.0, rate=100.0, entry_date="2024-06-01")
        t4 = TimeEntry(case_id=case1.id, service_code="IN_COURT", description="Plea hearing and sentencing (105th District)", hours=4.0, rate=100.0, entry_date=(now - timedelta(days=24)).strftime("%Y-%m-%d"))

        t5 = TimeEntry(case_id=case2.id, service_code="IN_COURT", description="Initial Appearance & Bond Conditions hearing", hours=2.0, rate=100.0, entry_date="2024-05-20")
        t6 = TimeEntry(case_id=case2.id, service_code="DRAFTING_MOTION", description="Drafted Motion for Discovery under Art. 39.14 CCP", hours=3.5, rate=100.0, entry_date="2024-06-15")

        t7 = TimeEntry(case_id=case3.id, service_code="JAIL_VISIT", description="Jail consultation regarding self-defense claims", hours=3.0, rate=100.0, entry_date="2023-11-20")
        t8 = TimeEntry(case_id=case3.id, service_code="DRAFTING_MOTION", description="Drafted Motion to Reduce Bail & Writ of Habeas Corpus", hours=4.5, rate=100.0, entry_date="2023-12-05")
        t9 = TimeEntry(case_id=case3.id, service_code="IN_COURT", description="Pre-Trial Motion Hearing (28th District)", hours=5.0, rate=100.0, entry_date="2024-02-14")

        session.add_all([t1, t2, t3, t4, t5, t6, t7, t8, t9])
        await session.commit()

        # --- 5. Events ---
        e1 = Event(case_id=case1.id, event_type="hearing", title="Arraignment & Plea Entry", description="105th District Court - Judge Pulcher presiding", event_date="2024-04-10")
        e2 = Event(case_id=case1.id, event_type="filing", title="Motion for Discovery Filed", description="Filed under Art. 39.14 CCP / Michael Morton Act", event_date="2024-05-02")
        e3 = Event(case_id=case1.id, event_type="hearing", title="Plea & Sentencing Hearing", description="Plea of Guilty to 3 yrs Deferred Adjudication", event_date=(now - timedelta(days=24)).strftime("%Y-%m-%d"))

        e4 = Event(case_id=case2.id, event_type="hearing", title="Docket Call & Status Hearing", description="94th District Court - Judge Galvan presiding (9:00 AM)", event_date=(now + timedelta(days=1)).strftime("%Y-%m-%d"))
        e5 = Event(case_id=case2.id, event_type="filing", title="State's Brady & 404(b) Notice", description="Received from Nueces County DA's Office", event_date="2024-06-20")

        e6 = Event(case_id=case3.id, event_type="hearing", title="Discovery Compliance Hearing", description="28th District Court - Judge Valdez presiding", event_date=(now + timedelta(days=8)).strftime("%Y-%m-%d"))

        session.add_all([e1, e2, e3, e4, e5, e6])
        await session.commit()

        # --- 6. Documents ---
        d1 = Document(
            case_id=case1.id,
            client_id=c1.id,
            filename="2024-CR-1042-D_Order_of_Deferred_Adjudication.pdf",
            doc_type="pdf",
            source="upload",
            content_text="CAUSE NO. 2024-CR-1042-D\nTHE STATE OF TEXAS VS. CARLOS RAMIREZ\nIN THE 105TH DISTRICT COURT OF NUECES COUNTY, TEXAS\nORDER OF DEFERRED ADJUDICATION\nOn this day came on to be considered the plea agreement...",
            classification_label="court_order",
            classification_confidence=0.98,
            created_at=datetime.now(timezone.utc) - timedelta(days=24)
        )
        d2 = Document(
            case_id=case2.id,
            client_id=c2.id,
            filename="CCPD_Offense_Report_24-051829.pdf",
            doc_type="pdf",
            source="upload",
            content_text="CORPUS CHRISTI POLICE DEPARTMENT\nINCIDENT REPORT: DWI 3RD OR MORE\nSuspect: Elena Trevino\nLocation: S. Padre Island Dr & Everhart Rd\nField Sobriety Tests conducted...",
            classification_label="police_report",
            classification_confidence=0.95,
            created_at=datetime.now(timezone.utc) - timedelta(days=40)
        )
        d3 = Document(
            case_id=case3.id,
            client_id=c3.id,
            filename="Nueces_DA_Michael_Morton_Compliance_Notice.pdf",
            doc_type="pdf",
            source="upload",
            content_text="STATE'S NOTICE OF COMPLIANCE PURSUANT TO ART. 39.14 TEXAS CODE OF CRIMINAL PROCEDURE\nCause No. 2023-CR-4819-A\nThe State of Texas hereby tenders the following discovery materials to Defense Counsel...",
            classification_label="discovery",
            classification_confidence=0.99,
            created_at=datetime.now(timezone.utc) - timedelta(days=60)
        )
        d4 = Document(
            case_id=case1.id,
            client_id=c1.id,
            filename="Nueces_Portal_2024-CR-1042-D_LiveCapture.txt",
            doc_type="court_record_lookup",
            source="nueces_odyssey_portal",
            content_text="Nueces County Odyssey Public Portal Smart Search Capture\nCase: 2024-CR-1042-D\nCourt: 105th District Court\nJudge: Jack Pulcher\nDefendant: Ramirez, Carlos\nCharge: POSS CS PG 1/1-B <1G\nRegister of Actions:\n- 03/15/2024 Indictment Filed\n- 04/10/2024 Arraignment\n- 08/25/2024 Order Deferred Adjudication Entered",
            classification_label="court_order",
            classification_confidence=1.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        session.add_all([d1, d2, d3, d4])
        await session.commit()

        # --- 7. Classification Labels ---
        labels = ["court_order", "correspondence", "pleading", "discovery", "invoice", "voucher_support", "police_report", "email", "uncategorized"]
        for lbl in labels:
            session.add(ClassificationLabel(name=lbl, description=f"{lbl} documents"))
        await session.commit()

        # --- 8. Canned Searches ---
        searches = [
            ("Unsubmitted Vouchers Expiring in < 15 Days", '{"voucher_urgency": "RED_ALERT"}'),
            ("All Open Appointed CJA Cases", '{"is_cja": true, "status": "OPEN"}'),
            ("Cases Pending Michael Morton Discovery", '{"stage": "DISCOVERY"}'),
            ("Documents Without Classification", '{}'),
        ]
        for q, f in searches:
            session.add(SearchHistory(query_text=q, filters_json=f, pinned=True, result_count=0))
        await session.commit()

        # --- 9. Portal Audit Log ---
        session.add(PortalAuditLog(
            portal="nueces_odyssey",
            client_name="2024-CR-1042-D (Ramirez, Carlos)",
            action="case_number",
            outcome="SUCCESS",
            performed_at=datetime.now(timezone.utc) - timedelta(days=2)
        ))
        await session.commit()

        print("South Texas & Corpus Christi Criminal Defense Seed Data populated successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
