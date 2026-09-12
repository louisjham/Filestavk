from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    case_number = Column(String, index=True)
    court = Column(String)  # e.g. "105th District Court", "Nueces County Court at Law #1"
    judge = Column(String)  # e.g. "Judge Jack Pulcher"
    case_type = Column(String)  # CRIMINAL, CIVIL, FAMILY, JUVENILE
    charge_description = Column(String)  # e.g. "Possession CS PG 1/1-B <1G (State Jail Felony)"
    status = Column(String)  # OPEN, CLOSED, PENDING, APPOINTED, DISPOSED
    stage = Column(String, default="DISCOVERY")  # ARREST, BOND, INDICTMENT, DISCOVERY, PRE_TRIAL, TRIAL, DISPOSED, PROBATION
    is_cja = Column(Boolean, default=False)
    in_custody = Column(Boolean, default=False)  # True if client is currently in Nueces County Jail
    jail_booking_date = Column(String)  # ISO Date e.g. "2024-07-15"
    jail_facility = Column(String, default="Nueces County Jail - Main")  # Facility name
    voucher_status = Column(String, default="NONE")  # NONE, UNBILLED, DRAFT, SUBMITTED, RETURNED, APPROVED, PAID
    bond_amount = Column(Float)
    bond_type = Column(String)  # SURETY, PR_BOND, CASH
    bond_conditions = Column(Text)  # "Ignition Interlock, Weekly urinalysis, No contact with co-def"
    morton_discovery_json = Column(Text)  # JSON tracking Art. 39.14 CCP discovery items
    has_appointment_order = Column(Boolean, default=False)  # True if Order Appointing Counsel is on docket
    appointment_order_date = Column(String)  # e.g. "2024-03-12"
    has_appointment_acceptance = Column(Boolean, default=False)  # True if file-stamped Acceptance is on docket
    acceptance_filed_date = Column(String)  # e.g. "2026-09-02"
    client_contact_date = Column(String)  # e.g. "2026-09-01"
    appointment_status = Column(String, default="UNKNOWN")  # CONFIRMED_AND_ACCEPTED, AWAITING_ACCEPTANCE, MISSING_ORDER, RETAINED, UNKNOWN

    disposition_type = Column(String)  # DISMISSED, PLEA_GUILTY, TRIAL_VERDICT, DEFERRED, PENDING
    disposition_date = Column(String)  # e.g. "2024-08-20"
    source_spreadsheet_row_id = Column(String)  # If imported from master spreadsheet
    opened_date = Column(String)
    closed_date = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    client = relationship("Client", back_populates="cases")
