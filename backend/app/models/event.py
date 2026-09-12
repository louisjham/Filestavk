from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    event_type = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_date = Column(String)
    created_at = Column(DateTime, default=func.now())
