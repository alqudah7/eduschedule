from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Lesson(Base):
    __tablename__ = "Lesson"

    id = Column(String, primary_key=True)
    teacher_id = Column("teacherId", String, ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    class_ = Column("class", String, nullable=False)
    room = Column(String, nullable=False)
    day = Column(String, nullable=False)
    start_time = Column("startTime", String, nullable=False)
    end_time = Column("endTime", String, nullable=False)
    school_level = Column("schoolLevel", String, nullable=False, default="ALL")
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())

    teacher = relationship("Teacher", back_populates="lessons")
