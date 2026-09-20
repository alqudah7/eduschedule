"""Multi-tenant hierarchy models.

Organization -> School -> everything else.

Enum-like fields (plan, status, locale_default) are stored as VARCHAR at
the DB level with CHECK constraints, per MULTITENANT.md §0 decision #3.
Python-side we surface literal-typed Enums for editor autocomplete and
validation.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    billing_email = Column(Text, nullable=True)
    plan = Column(String(32), nullable=False, server_default="TRIAL")
    status = Column(String(32), nullable=False, server_default="ACTIVE")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    schools = relationship("School", back_populates="organization")

    __table_args__ = (
        CheckConstraint("plan IN ('TRIAL', 'STANDARD', 'GROUP')", name="ck_org_plan"),
        CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED')", name="ck_org_status",
        ),
        UniqueConstraint("slug", name="uq_organizations_slug"),
    )


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    country = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False)
    locale_default = Column(String(8), nullable=False)
    logo_url = Column(Text, nullable=True)
    primary_color = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, server_default="ACTIVE")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    organization = relationship("Organization", back_populates="schools")
    settings = relationship("SchoolSettings", back_populates="school", uselist=False)

    __table_args__ = (
        CheckConstraint("locale_default IN ('EN', 'AR')", name="ck_school_locale"),
        CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'TRIAL')", name="ck_school_status",
        ),
        UniqueConstraint("slug", name="uq_schools_slug"),
    )


class SchoolSettings(Base):
    __tablename__ = "school_settings"

    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    working_days = Column(ARRAY(Text), nullable=False)
    school_levels = Column(ARRAY(Text), nullable=False)
    supported_locales = Column(ARRAY(Text), nullable=False)
    periods = Column(JSONB, nullable=False)
    breaks = Column(JSONB, nullable=False)
    grade_labels = Column(JSONB, nullable=True)
    features_enabled = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    school = relationship("School", back_populates="settings")
