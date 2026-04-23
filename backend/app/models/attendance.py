from sqlalchemy import Column, String, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base


class TeacherAttendance(Base):
    __tablename__ = "teacher_attendance"

    id = Column(String, primary_key=True)
    teacher_id = Column(String, ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # present | absent | late
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    teacher = relationship("Teacher", back_populates="attendances")

    __table_args__ = (
        UniqueConstraint("teacher_id", "date", name="uq_teacher_attendance_date"),
    )
