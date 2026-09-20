from sqlalchemy import (
    ARRAY,
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

# school_level values: PRESCHOOL | ELEMENTARY | MIDDLE | HIGH | ALL
# (PRESCHOOL is a canonical value that had been missing from the TS
# type union — see MULTITENANT.md §4 and AUDIT.md #47.)


class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True)
    # Global email uniqueness has been replaced by (school_id, email) via
    # migration 8878824788ec. The Python-level unique=True is dropped so
    # the model reflects the DB state and autogenerate doesn't propose
    # putting the constraint back.
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="TEACHER")
    school_id = Column(
        "school_id", Integer,
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column("createdAt", DateTime(timezone=True), server_default=func.now())
    updated_at = Column("updatedAt", DateTime(timezone=True), onupdate=func.now())

    teacher = relationship("Teacher", back_populates="user", uselist=False)

    __table_args__ = (
        UniqueConstraint("school_id", "email", name="uq_user_school_email"),
    )


class Teacher(Base):
    __tablename__ = "Teacher"

    id = Column(String, primary_key=True)
    user_id = Column("userId", String, ForeignKey("User.id", ondelete="CASCADE"), unique=True)
    name = Column(String, nullable=False)
    initials = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, nullable=False)  # uniqueness is now (school_id, email)
    phone = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")
    max_duties = Column("maxDuties", Integer, nullable=False, default=16)
    qualifications = Column(ARRAY(String), nullable=False, default=[])
    subjects = Column(ARRAY(String), nullable=False, default=[])
    school_level = Column("schoolLevel", String, nullable=False, default="ALL")
    school_id = Column(
        "school_id", Integer,
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    attendances = relationship("TeacherAttendance", back_populates="teacher")

    __table_args__ = (
        UniqueConstraint("school_id", "email", name="uq_teacher_school_email"),
    )
