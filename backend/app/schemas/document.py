from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    case_id: Optional[int] = None
    client_id: Optional[int] = None
    filename: str
    doc_type: Optional[str] = None
    source: Optional[str] = None
    content_text: Optional[str] = None
    metadata_json: Optional[str] = None
    classification_label: Optional[str] = None
    classification_confidence: Optional[float] = None
    ingested_at: Optional[datetime] = None

class DocumentOut(DocumentBase):
    id: int
    filepath: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
