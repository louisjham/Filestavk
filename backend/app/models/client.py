from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    dob = Column(String)
    address = Column(String)
    phone = Column(String)
    email = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    cases = relationship("Case", back_populates="client")
