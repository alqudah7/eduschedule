"""create tenancy tables

Adds the three tables that define the multi-tenant hierarchy per
MULTITENANT.md §2:

  organizations   (root of the hierarchy)
  schools         (a school belongs to one org)
  school_settings (one row per school, per-tenant configuration)

Columns are normalised where scalar and jsonb where the shape varies
(§0 decision #3). Enum-like fields are stored as VARCHAR with a CHECK
constraint rather than a Postgres ENUM, because ALTER TYPE ADD VALUE
is one-way and complicates future rollout.

Revision ID: ac08810385eb
Revises: 21b21e11f5af
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ac08810385eb"
down_revision: Union[str, None] = "21b21e11f5af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("billing_email", sa.Text(), nullable=True),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="TRIAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("plan IN ('TRIAL', 'STANDARD', 'GROUP')", name="ck_org_plan"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED')", name="ck_org_status",
        ),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id", sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("locale_default", sa.String(length=8), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("locale_default IN ('EN', 'AR')", name="ck_school_locale"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'TRIAL')", name="ck_school_status",
        ),
        sa.UniqueConstraint("slug", name="uq_schools_slug"),
    )
    op.create_index(
        "ix_schools_organization_id", "schools", ["organization_id"],
    )

    op.create_table(
        "school_settings",
        sa.Column("school_id", sa.Integer(),
                  sa.ForeignKey("schools.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("working_days", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("school_levels", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("supported_locales", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("periods", postgresql.JSONB(), nullable=False),
        sa.Column("breaks", postgresql.JSONB(), nullable=False),
        sa.Column("grade_labels", postgresql.JSONB(), nullable=True),
        sa.Column("features_enabled", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("school_settings")
    op.drop_index("ix_schools_organization_id", table_name="schools")
    op.drop_table("schools")
    op.drop_table("organizations")
