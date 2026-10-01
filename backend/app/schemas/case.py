from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CaseBase(BaseModel):
    client_id: int
    case_number: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    case_type: Optional[str] = None
    charge_description: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = "DISCOVERY"
    is_cja: Optional[bool] = False
    in_custody: Optional[bool] = False
    jail_booking_date: Optional[str] = None
    jail_facility: Optional[str] = "Nueces County Jail - Main"
    voucher_status: Optional[str] = "NONE"
    bond_amount: Optional[float] = None
    bond_type: Optional[str] = None
    bond_conditions: Optional[str] = None
    morton_discovery_json: Optional[str] = None
    has_appointment_order: Optional[bool] = False
    appointment_order_date: Optional[str] = None
    has_appointment_acceptance: Optional[bool] = False
    acceptance_filed_date: Optional[str] = None
    client_contact_date: Optional[str] = None
    appointment_status: Optional[str] = "UNKNOWN"
    appellate_case_number: Optional[str] = None
    trial_court_case_number: Optional[str] = None
    appellate_court: Optional[str] = None
    appellate_brief_due_date: Optional[str] = None
    appellate_extension_count: Optional[int] = 0
    appellate_extension_reason: Optional[str] = None
    appellate_motion_status: Optional[str] = None
    disposition_type: Optional[str] = None
    disposition_date: Optional[str] = None
    source_spreadsheet_row_id: Optional[str] = None
    opened_date: Optional[str] = None
    closed_date: Optional[str] = None
    notes: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    client_id: Optional[int] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    case_type: Optional[str] = None
    charge_description: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    is_cja: Optional[bool] = None
    in_custody: Optional[bool] = None
    jail_booking_date: Optional[str] = None
    jail_facility: Optional[str] = None
    voucher_status: Optional[str] = None
    bond_amount: Optional[float] = None
    bond_type: Optional[str] = None
    bond_conditions: Optional[str] = None
    morton_discovery_json: Optional[str] = None
    has_appointment_order: Optional[bool] = None
    appointment_order_date: Optional[str] = None
    has_appointment_acceptance: Optional[bool] = None
    acceptance_filed_date: Optional[str] = None
    client_contact_date: Optional[str] = None
    appointment_status: Optional[str] = None
    appellate_case_number: Optional[str] = None
    trial_court_case_number: Optional[str] = None
    appellate_court: Optional[str] = None
    appellate_brief_due_date: Optional[str] = None
    appellate_extension_count: Optional[int] = None
    appellate_extension_reason: Optional[str] = None
    appellate_motion_status: Optional[str] = None
    disposition_type: Optional[str] = None
    disposition_date: Optional[str] = None
    source_spreadsheet_row_id: Optional[str] = None
    opened_date: Optional[str] = None
    closed_date: Optional[str] = None
    notes: Optional[str] = None


class CaseOut(CaseBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

