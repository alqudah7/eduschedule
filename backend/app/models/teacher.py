from sqlalchemy import Column, String, Integer, ARRAY, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="TEACHER")
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())
    updated_at = Column("updatedAt", DateTime(timezone=True), onupdate=func.now())

    teacher = relationship("Teacher", back_populates="user", uselist=False)


class Teacher(Base):
    __tablename__ = "Teacher"

    id = Column(String, primary_key=True)
    user_id = Column("userId", String, ForeignKey("User.id", ondelete="CASCADE"), unique=True)
    name = Column(String, nullable=False)
    initials = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")
    max_duties = Column("maxDuties", Integer, nullable=False, default=16)
    qualifications = Column(ARRAY(String), nullable=False, default=[])
    subjects = Column(ARRAY(String), nullable=False, default=[])
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())
    updated_at = Column("updatedAt", DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="teacher")
    duties = relationship("Duty", back_populates="teacher")
    lessons = relationship("Lesson", back_populates="teacher")
    substitutions_given = relationship(
        "Substitution", back_populates="substitute", foreign_keys="Substitution.substitute_id"
    )
    substitutions_received = relationship(
        "Substitution", back_populates="absent_teacher", foreign_keys="Substitution.absent_teacher_id"
    )
    absences = relationship("Absence", back_populates="teacher")
