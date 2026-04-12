from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    __tablename__ = "Alert"

    id = Column(String, primary_key=True)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    duty_id = Column("dutyId", String, ForeignKey("Duty.id", ondelete="SET NULL"), nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())

    duty = relationship("Duty", back_populates="alerts")


class Absence(Base):
    __tablename__ = "Absence"

    id = Column(String, primary_key=True)
    teacher_id = Column("teacherId", String, ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())

    teacher = relationship("Teacher", back_populates="absences")


class AuditLog(Base):
    __tablename__ = "AuditLog"

    id = Column(String, primary_key=True)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    details = Column(String, nullable=False)
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())
