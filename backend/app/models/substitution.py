from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Substitution(Base):
    __tablename__ = "Substitution"

    id = Column(String, primary_key=True)
    # Previous unique=True (global per-dutyId) migrated to composite
    # (school_id, dutyId) via revision 28c532490174 — see __table_args__.
    duty_id = Column("dutyId", String, ForeignKey("Duty.id", ondelete="CASCADE"), nullable=True)
    lesson_id = Column("lessonId", String, ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=True)
    absent_teacher_id = Column("absentTeacherId", String, ForeignKey("Teacher.id"), nullable=False)
    substitute_id = Column("substituteId", String, ForeignKey("Teacher.id"), nullable=True)
    status = Column(String, nullable=False, default="PENDING")
    requested_at = Column("requestedAt", DateTime(timezone=True), server_default=func.now())
    resolved_at = Column("resolvedAt", DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)
    school_id = Column(
        "school_id", Integer,
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
    )

    duty = relationship("Duty", back_populates="substitution")
    lesson = relationship("Lesson", foreign_keys=[lesson_id])
    absent_teacher = relationship("Teacher", back_populates="substitutions_received", foreign_keys=[absent_teacher_id])
    substitute = relationship("Teacher", back_populates="substitutions_given", foreign_keys=[substitute_id])

    # UniqueConstraint takes DB column names, not Python attribute names —
    # this Column's DB name is "dutyId" per its Column() arg.
    __table_args__ = (
        UniqueConstraint("school_id", "dutyId", name="uq_substitution_school_duty"),
    )
