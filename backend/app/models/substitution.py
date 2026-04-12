from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Substitution(Base):
    __tablename__ = "substitutions"

    id = Column(String, primary_key=True)
    duty_id = Column(String, ForeignKey("duties.id", ondelete="CASCADE"), unique=True, nullable=False)
    absent_teacher_id = Column(String, ForeignKey("teachers.id"), nullable=False)
    substitute_id = Column(String, ForeignKey("teachers.id"), nullable=True)
    status = Column(String, nullable=False, default="PENDING")
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)

    duty = relationship("Duty", back_populates="substitution")
    absent_teacher = relationship("Teacher", back_populates="substitutions_received", foreign_keys=[absent_teacher_id])
    substitute = relationship("Teacher", back_populates="substitutions_given", foreign_keys=[substitute_id])
