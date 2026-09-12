from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class DocumentRuleBase(BaseModel):
    document_type: str
    display_name: str
    description: Optional[str] = None
    lifecycle_stage: Optional[str] = "Pretrial - Magistrate Hearing"
    target_case_stage: Optional[str] = "MAGISTRATE_HEARING"
    target_case_status: Optional[str] = "open"
    is_cja_default: Optional[bool] = True
    set_has_appointment_order: Optional[bool] = False
    set_has_appointment_acceptance: Optional[bool] = False
    set_appointment_status: Optional[str] = "UNKNOWN"
    auto_populate_client: Optional[bool] = True
    auto_populate_case: Optional[bool] = True
    create_docket_event: Optional[bool] = True
    event_type: Optional[str] = "order"
    event_title_template: Optional[str] = "{doc_title} Filed ({court})"
    event_desc_template: Optional[str] = "{doc_title} processed for {defendant_name}."
    trigger_statutory_deadline: Optional[bool] = False
    statutory_basis: Optional[str] = None
    deadline_name: Optional[str] = None
    deadline_hours_offset: Optional[int] = 48
    confidence_threshold: Optional[float] = 0.70
    require_human_verification: Optional[bool] = False
    is_active: Optional[bool] = True
    custom_actions_json: Optional[str] = "{}"

class DocumentRuleCreate(DocumentRuleBase):
    pass

class DocumentRuleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    target_case_stage: Optional[str] = None
    target_case_status: Optional[str] = None
    is_cja_default: Optional[bool] = None
    set_has_appointment_order: Optional[bool] = None
    set_has_appointment_acceptance: Optional[bool] = None
    set_appointment_status: Optional[str] = None

    auto_populate_client: Optional[bool] = None
    auto_populate_case: Optional[bool] = None
    create_docket_event: Optional[bool] = None
    event_type: Optional[str] = None
    event_title_template: Optional[str] = None
    event_desc_template: Optional[str] = None
    trigger_statutory_deadline: Optional[bool] = None
    statutory_basis: Optional[str] = None
    deadline_name: Optional[str] = None
    deadline_hours_offset: Optional[int] = None
    confidence_threshold: Optional[float] = None
    require_human_verification: Optional[bool] = None
    is_active: Optional[bool] = None
    custom_actions_json: Optional[str] = None

class DocumentRuleOut(DocumentRuleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
