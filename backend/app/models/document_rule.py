from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base

class DocumentRule(Base):
    __tablename__ = "document_rules"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String, unique=True, index=True, nullable=False)  # e.g. "appointment_order", "waiver_of_arraignment"
    display_name = Column(String, nullable=False)
    description = Column(Text)
    lifecycle_stage = Column(String, default="Pretrial - Magistrate Hearing")
    target_case_stage = Column(String, default="MAGISTRATE_HEARING")  # MAGISTRATE_HEARING, PRE_TRIAL, DISCOVERY, TRIAL, DISPOSED
    target_case_status = Column(String, default="open")
    is_cja_default = Column(Boolean, default=True)
    set_has_appointment_order = Column(Boolean, default=False)
    set_has_appointment_acceptance = Column(Boolean, default=False)
    set_appointment_status = Column(String, default="UNKNOWN")  # CONFIRMED_AND_ACCEPTED, AWAITING_ACCEPTANCE, MISSING_ORDER, UNKNOWN
    auto_populate_client = Column(Boolean, default=True)  # Populates DOB, phone, address, etc.
    auto_populate_case = Column(Boolean, default=True)  # Populates charge, court, judge, in_custody
    create_docket_event = Column(Boolean, default=True)
    event_type = Column(String, default="order")  # order, pleading, hearing, discovery, voucher, deadline
    event_title_template = Column(String, default="{doc_title} Filed ({court})")
    event_desc_template = Column(Text, default="{doc_title} processed for {defendant_name}.")
    trigger_statutory_deadline = Column(Boolean, default=False)
    statutory_basis = Column(String)  # e.g. "Tex. Code Crim. Proc. art. 26.04(j)(1)"
    deadline_name = Column(String)  # e.g. "48-Hour Client Contact Acknowledgment Rule"
    deadline_hours_offset = Column(Integer, default=48)  # Hours from document receipt
    confidence_threshold = Column(Float, default=0.70)
    require_human_verification = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    custom_actions_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())


# Grounded Nueces County Default Rules Seed Data
DEFAULT_DOCUMENT_RULES = [
    {
        "document_type": "appointment_order",
        "display_name": "Order of Appointment of Attorney (Art. 26.04 CCP)",
        "description": "Formal magistrate assignment of defense counsel (Kimbel Brandon). Awaiting file-stamped attorney acceptance before voucher billing qualification.",
        "lifecycle_stage": "Pretrial - Magistrate Hearing",
        "target_case_stage": "MAGISTRATE_HEARING",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": True,
        "set_has_appointment_acceptance": False,
        "set_appointment_status": "AWAITING_ACCEPTANCE",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "order",
        "event_title_template": "Order of Appointment Issued by Court ({court})",
        "event_desc_template": "Court appointed {attorney_name} (SBN: {sbn}) to represent {defendant_name} on charge {charge}. Acknowledgment must be filed with District Clerk within 48h.",
        "trigger_statutory_deadline": True,
        "statutory_basis": "Tex. Code Crim. Proc. art. 26.04(j)(1)",
        "deadline_name": "Art. 26.04(j)(1) 48-Hour Client Contact & Acknowledgment Rule",
        "deadline_hours_offset": 48,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"set_in_custody": false, "default_court_type": "COUNTY_COURT_AT_LAW"}'
    },
    {
        "document_type": "appointment_acceptance",
        "display_name": "Acceptance of Appointment & Client Contact (Art. 26.04(j)(1))",
        "description": "Signed attorney acceptance and District Clerk file stamp confirming client contact and formal representation, required for County Auditor voucher payment.",
        "lifecycle_stage": "Pretrial - Representation Confirmed",
        "target_case_stage": "MAGISTRATE_HEARING",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": True,
        "set_has_appointment_acceptance": True,
        "set_appointment_status": "CONFIRMED_AND_ACCEPTED",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "filing",
        "event_title_template": "Acceptance of Appointment Filed with District Clerk ({court})",
        "event_desc_template": "Attorney acceptance and initial client contact filed with District Clerk for {defendant_name}. Appointment verified and qualified for voucher payment.",
        "trigger_statutory_deadline": False,
        "statutory_basis": "Tex. Code Crim. Proc. art. 26.04(j)(1) & 26.05",
        "deadline_name": None,
        "deadline_hours_offset": 0,
        "confidence_threshold": 0.75,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"voucher_qualified": true}'
    },

    {
        "document_type": "waiver_of_arraignment",
        "display_name": "Waiver of Arraignment & Entry of Plea",
        "description": "Formal defendant pleading under Tex. Code Crim. Proc. art. 27.18/27.19 waiving formal reading of information and entering Not Guilty plea.",
        "lifecycle_stage": "Arraignment Waived / Pre-Trial",
        "target_case_stage": "PRE_TRIAL",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "VERIFIED_ON_DOCKET",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "pleading",
        "event_title_template": "Waiver of Arraignment Filed ({court})",
        "event_desc_template": "Waiver of Arraignment filed for {defendant_name}. Plea entered: Not Guilty; requested Pre-Trial & Jury Trial settings.",
        "trigger_statutory_deadline": False,
        "statutory_basis": "Tex. Code Crim. Proc. art. 27.18 / 27.19",
        "deadline_name": None,
        "deadline_hours_offset": 0,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"plea": "Not Guilty", "requested_settings": ["Pre-Trial", "Jury Trial"]}'
    },
    {
        "document_type": "discovery",
        "display_name": "Michael Morton Discovery Compliance (Art. 39.14 CCP)",
        "description": "State's disclosure and production of offense reports, witness statements, videos, and Brady exculpatory evidence under Art. 39.14 CCP.",
        "lifecycle_stage": "Discovery / Morton Compliance",
        "target_case_stage": "DISCOVERY",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "UNKNOWN",
        "auto_populate_client": False,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "discovery",
        "event_title_template": "Michael Morton Discovery Packet Filed (Art. 39.14 CCP)",
        "event_desc_template": "State compliance notice and discovery packet produced under Art. 39.14 CCP for {defendant_name}.",
        "trigger_statutory_deadline": True,
        "statutory_basis": "Tex. Code Crim. Proc. art. 39.14",
        "deadline_name": "Art. 39.14 Discovery Review & Acknowledgment Notice",
        "deadline_hours_offset": 336,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"update_morton_tracker": true}'
    },
    {
        "document_type": "court_order",
        "display_name": "Court Order / Judicial Ruling",
        "description": "Signed judicial orders including bond conditions, continuances, reset settings, or dismissals in Nueces County courts.",
        "lifecycle_stage": "Judicial Order Entered",
        "target_case_stage": "PRE_TRIAL",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "UNKNOWN",
        "auto_populate_client": False,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "order",
        "event_title_template": "Court Order Signed ({court})",
        "event_desc_template": "Judicial order entered by {judge} in Cause No. {case_number}.",
        "trigger_statutory_deadline": False,
        "statutory_basis": "Texas Rules of Criminal Procedure",
        "deadline_name": None,
        "deadline_hours_offset": 0,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": "{}"
    },
    {
        "document_type": "police_report",
        "display_name": "Police Incident / Offense Narrative (CCPD / NCSO)",
        "description": "Corpus Christi Police Department or Nueces County Sheriff offense report, narrative, and arrest probable cause affidavit.",
        "lifecycle_stage": "Arrest / Offense Documentation",
        "target_case_stage": "DISCOVERY",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "UNKNOWN",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "discovery",
        "event_title_template": "Law Enforcement Offense Report Ingested ({court})",
        "event_desc_template": "Police narrative and offense details cataloged in case repository for {defendant_name}.",
        "trigger_statutory_deadline": False,
        "statutory_basis": "Texas Penal Code",
        "deadline_name": None,
        "deadline_hours_offset": 0,
        "confidence_threshold": 0.65,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": "{}"
    },
    {
        "document_type": "hearing_notice",
        "display_name": "Hearing Notice / Docket Call Setting",
        "description": "Formal notice of appearance date for Arraignment, Pre-Trial Conference, Suppression Hearing, or Trial.",
        "lifecycle_stage": "Docket Setting Scheduled",
        "target_case_stage": "PRE_TRIAL",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "UNKNOWN",
        "auto_populate_client": False,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "hearing",
        "event_title_template": "Court Setting Scheduled ({court})",
        "event_desc_template": "Appearance scheduled on {hearing_datetime} before {judge}.",
        "trigger_statutory_deadline": True,
        "statutory_basis": "Nueces County Local Rules of Court",
        "deadline_name": "Court Appearance Calendar Reminder",
        "deadline_hours_offset": 72,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": "{}"
    },
    {
        "document_type": "warrant_remittance",
        "display_name": "Nueces County Auditor Remittance Advice",
        "description": "Payment warrant notice from Nueces County Auditor for approved CJA voucher fee claims under Tex. Code Crim. Proc. art. 26.05.",
        "lifecycle_stage": "Voucher Paid / Financial Settlement",
        "target_case_stage": "DISPOSED",
        "target_case_status": "closed",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "UNKNOWN",
        "auto_populate_client": False,
        "auto_populate_case": False,
        "create_docket_event": True,
        "event_type": "voucher",
        "event_title_template": "Auditor Fee Warrant Issued (#{warrant_number})",
        "event_desc_template": "County payment warrant #{warrant_number} issued for ${amount_paid}.",
        "trigger_statutory_deadline": False,
        "statutory_basis": "Tex. Code Crim. Proc. art. 26.05",
        "deadline_name": None,
        "deadline_hours_offset": 0,
        "confidence_threshold": 0.70,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"update_voucher_status": "PAID"}'
    },
    {
        "document_type": "appellate_motion_extension",
        "display_name": "Motion to Extend Time for Filing Appellant's Brief (TRAP 10.5 / 38.6)",
        "description": "Formal written request submitted to Texas Court of Appeals (13th District) asking for enlarged deadline to file Appellant's Brief with Statement of Good Cause.",
        "lifecycle_stage": "Appellate Briefing / Extension Pending",
        "target_case_stage": "APPEAL",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "CONFIRMED_AND_ACCEPTED",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "pleading",
        "event_title_template": "{doc_title} Filed ({court})",
        "event_desc_template": "Counsel filed {motion_sequence} Motion to Extend Time for Filing Appellant's Brief to {extended_due_date} in Cause No. {case_number}. Good cause cited: {good_cause_summary}.",
        "trigger_statutory_deadline": True,
        "statutory_basis": "Tex. R. App. P. 10.5(b) & 38.6(d)",
        "deadline_name": "Requested Appellant's Brief Extension Due Date",
        "deadline_hours_offset": 720,  # 30-day default
        "confidence_threshold": 0.75,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"appellate_motion_status": "MOTION_PENDING"}'
    },
    {
        "document_type": "appellate_order_granting_extension",
        "display_name": "Order Granting Extension of Time to File Appellant's Brief",
        "description": "Official communication and ruling from the Court of Appeals confirming Appellant's motion for extension of time was GRANTED and setting new calendar due date.",
        "lifecycle_stage": "Appellate Briefing / Extension Granted",
        "target_case_stage": "APPEAL",
        "target_case_status": "open",
        "is_cja_default": True,
        "set_has_appointment_order": False,
        "set_appointment_status": "CONFIRMED_AND_ACCEPTED",
        "auto_populate_client": True,
        "auto_populate_case": True,
        "create_docket_event": True,
        "event_type": "order",
        "event_title_template": "Extension of Time to File Brief GRANTED by {court}",
        "event_desc_template": "Court of Appeals GRANTED Appellant's motion for extension of time. Appellant's Brief officially extended to {extended_due_date}.",
        "trigger_statutory_deadline": True,
        "statutory_basis": "Tex. R. App. P. 38.6(d)",
        "deadline_name": "Court-Granted Appellant's Brief Due Date",
        "deadline_hours_offset": 720,
        "confidence_threshold": 0.80,
        "require_human_verification": False,
        "is_active": True,
        "custom_actions_json": '{"appellate_motion_status": "EXTENSION_GRANTED"}'
    }
]

