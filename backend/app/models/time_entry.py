from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    service_code = Column(String)  # IN_COURT, OUT_OF_COURT, JAIL_VISIT, DRAFTING_MOTION, CLIENT_CONFERENCE, DISCOVERY_REVIEW
    description = Column(Text)
    hours = Column(Float)
    rate = Column(Float, default=100.0)  # Texas Fair Defense Act Nueces County hourly fee rate
    entry_date = Column(String)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now())

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    voucher_number = Column(String, index=True)  # e.g. "VCH-2024-1042"
    voucher_type = Column(String, default="CJA-FELONY")  # CJA-FELONY, CJA-MISDEMEANOR, CJA-APPEAL, EXPENSE-INVESTIGATOR
    status = Column(String, default="UNBILLED")  # UNBILLED, DRAFT, SUBMITTED, RETURNED, APPROVED, PAID
    amount_requested = Column(Float, default=0.0)
    amount_approved = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    disposition_date = Column(String)  # Plea/Dismissal/Verdict date (kicks off 30-day clock)
    submission_deadline = Column(String, nullable=True)  # Optional target/reminder date
    submission_method = Column(String, default="ONLINE_PORTAL")  # ONLINE_PORTAL, PAPER_HAND_SUBMITTED, UNVOUCHERED_LEGACY
    has_appointment_order_verified = Column(Boolean, default=True)  # True if appointment order is in place
    submitted_date = Column(String)
    approved_date = Column(String)
    paid_date = Column(String)
    warrant_number = Column(String)  # Nueces County Auditor check / warrant #
    rejection_reason = Column(Text)  # If RETURNED: e.g. "Itemize in-court hearing dates and attach docket sheet"
    itemized_json = Column(Text)  # JSON breakdown of line items
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
