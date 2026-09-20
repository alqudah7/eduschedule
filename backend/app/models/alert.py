from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
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
    school_id = Column(
        "school_id", Integer,
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())

    duty = relationship("Duty", back_populates="alerts")


# Absence was merged into TeacherAttendance in Alembic revision
# 21c773d1e916 (AUDIT #28). Callers now read attendance rows filtered
# by status='absent'. Teacher.absences is a property computed from
# Teacher.attendances so the interface didn't change.


class AuditLog(Base):
    __tablename__ = "AuditLog"

    id = Column(String, primary_key=True)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    details = Column(String, nullable=False)
    school_id = Column(
        "school_id", Integer,
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())
