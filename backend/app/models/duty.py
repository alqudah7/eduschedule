from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Duty(Base):
    __tablename__ = "duties"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    day = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    location = Column(String, nullable=False)
    teacher_id = Column(String, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="CONFIRMED")
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    teacher = relationship("Teacher", back_populates="duties")
    substitution = relationship("Substitution", back_populates="duty", uselist=False)
    alerts = relationship("Alert", back_populates="duty")
