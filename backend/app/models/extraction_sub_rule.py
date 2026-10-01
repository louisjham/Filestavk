from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class ExtractionSubRule(Base):
    __tablename__ = "extraction_sub_rules"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String, index=True, nullable=False)  # e.g. "appellate_order_granting_extension", "appointment_order", "all"
    field_name = Column(String, index=True, nullable=False)     # e.g. "court", "judge", "case_number", "extended_due_date"
    rule_type = Column(String, default="REGEX_PATTERN")        # REGEX_PATTERN, ANCHOR_EXTRACTION, CONSTANT_OVERRIDE
    pattern_or_value = Column(Text, nullable=False)             # Regex pattern or explicit override value
    sample_text_snippet = Column(Text, nullable=True)           # Surrounding context anchor for verification
    capture_group = Column(Integer, default=1)                  # Regex capture group index
    is_active = Column(Boolean, default=True)
    learned_from_doc_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(String, default="attorney")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
