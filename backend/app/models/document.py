from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String)
    doc_type = Column(String)
    source = Column(String)
    content_text = Column(Text)
    metadata_json = Column(Text)
    classification_label = Column(String)
    classification_confidence = Column(Float)
    ingested_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
