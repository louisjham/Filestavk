from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class ClassificationLabel(Base):
    __tablename__ = "classification_labels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

class DocumentLabel(Base):
    __tablename__ = "document_labels"
    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    label_id = Column(Integer, ForeignKey("classification_labels.id"), primary_key=True)
    is_manual = Column(Boolean, default=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=func.now())

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String)
    status = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    records_found = Column(Integer, default=0)
    records_saved = Column(Integer, default=0)
    error_log = Column(Text)

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text)
    filters_json = Column(Text)
    result_count = Column(Integer)
    executed_at = Column(DateTime, default=func.now())
    pinned = Column(Boolean, default=False)

class PortalAuditLog(Base):
    __tablename__ = "portal_audit_log"
    id = Column(Integer, primary_key=True, index=True)
    portal = Column(String)
    client_name = Column(String)
    action = Column(String)
    outcome = Column(String)
    error_message = Column(Text)
    performed_at = Column(DateTime, default=func.now())

class RawEmailStaging(Base):
    __tablename__ = "raw_email_staging"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, index=True)
    sender = Column(String)
    recipient = Column(String)
    subject = Column(String)
    date_sent = Column(String)
    file_path = Column(String)
    raw_size_bytes = Column(Integer, default=0)
    filter_tag = Column(String, default="UNCATEGORIZED")
    etl_status = Column(String, default="STAGED")  # STAGED, PARSED, VERIFIED_COMMITTED, REJECTED
    extracted_data_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=func.now())
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)

