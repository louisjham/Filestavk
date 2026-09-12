from pydantic import BaseModel, field_validator
import re
from typing import Optional
from datetime import datetime

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class ClientBase(BaseModel):
    name: str
    dob: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        if not v:
            return None
        v_str = str(v).strip()
        if not v_str:
            return None
        digits = re.sub(r'\D', '', v_str)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        if len(digits) == 10:
            return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
        raise ValueError("Phone number must contain exactly 10 digits in format (XXX) XXX-XXXX")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        if not v:
            return None
        v_str = str(v).strip().lower()
        if not v_str:
            return None
        # Strip any leading phone number if merged
        if '@' in v_str:
            user_part, dom_part = v_str.split('@', 1)
            clean_user = re.sub(r'^(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{7,10})[-.\s]*', '', user_part)
            if clean_user:
                v_str = f"{clean_user}@{dom_part}"
        if not EMAIL_REGEX.match(v_str):
            raise ValueError("Invalid email format (expected username@domain.tld)")
        return v_str

class ClientCreate(ClientBase):
    in_custody: Optional[bool] = False

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    in_custody: Optional[bool] = None

class ClientOut(ClientBase):
    id: int
    case_count: Optional[int] = 0
    case_numbers: Optional[list[str]] = []
    has_active_cases: Optional[bool] = False
    is_in_custody: Optional[bool] = False
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
