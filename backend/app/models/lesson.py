from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(String, primary_key=True)
    teacher_id = Column(String, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    class_ = Column("class", String, nullable=False)
    room = Column(String, nullable=False)
    day = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    teacher = relationship("Teacher", back_populates="lessons")
