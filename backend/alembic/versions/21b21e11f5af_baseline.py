"""baseline — pre-Alembic schema

Historically this revision was empty because production had been created
by app-startup `Base.metadata.create_all` + `_run_column_migrations`
before Alembic was introduced. We stamped prod at this revision so
subsequent migrations layered on top.

That approach fails for a scratch database (fresh dev environment or a
full restore from CSV backup) — there is nothing to layer onto.

`upgrade()` now creates the pre-Alembic schema explicitly. Production is
still stamped at this revision (`alembic stamp 21b21e11f5af` was applied
before we ran the tenancy chain), so this DDL DOES NOT re-execute against
production — Alembic will not re-run a revision the database is already
past. Fresh databases go through it. The DDL matches what SQLAlchemy's
`Base.metadata.create_all` would produce for the pre-tenancy models —
VARCHAR everywhere, no Postgres enums.

Revision ID: 21b21e11f5af
Revises:
Create Date: 2026-09-20 10:34:56.533629
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = "21b21e11f5af"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── User ──────────────────────────────────────────────────────────────
    op.create_table(
        "User",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="TEACHER"),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Teacher ───────────────────────────────────────────────────────────
    op.create_table(
        "Teacher",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("userId", sa.String(),
                  sa.ForeignKey("User.id", ondelete="CASCADE"), unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("initials", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("maxDuties", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("qualifications", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("subjects", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("schoolLevel", sa.String(), nullable=False, server_default="ALL"),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Duty ──────────────────────────────────────────────────────────────
    op.create_table(
        "Duty",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("day", sa.String(), nullable=False),
        sa.Column("startTime", sa.String(), nullable=False),
        sa.Column("endTime", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("teacherId", sa.String(),
                  sa.ForeignKey("Teacher.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="CONFIRMED"),
        sa.Column("dutyCategory", sa.String(), nullable=False, server_default="SUPERVISION"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Lesson ────────────────────────────────────────────────────────────
    op.create_table(
        "Lesson",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacherId", sa.String(),
                  sa.ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("class", sa.String(), nullable=False),
        sa.Column("room", sa.String(), nullable=False),
        sa.Column("day", sa.String(), nullable=False),
        sa.Column("startTime", sa.String(), nullable=False),
        sa.Column("endTime", sa.String(), nullable=False),
        sa.Column("schoolLevel", sa.String(), nullable=False, server_default="ALL"),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── Substitution ──────────────────────────────────────────────────────
    # Note: originally had UNIQUE (dutyId). Revision 8878824788ec later
    # migrated it to per-school unique; keep the historically-correct
    # constraint here so downgrade to base restores the original.
    op.create_table(
        "Substitution",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dutyId", sa.String(),
                  sa.ForeignKey("Duty.id", ondelete="CASCADE"),
                  unique=True, nullable=True),
        sa.Column("lessonId", sa.String(),
                  sa.ForeignKey("Lesson.id", ondelete="CASCADE"), nullable=True),
        sa.Column("absentTeacherId", sa.String(),
                  sa.ForeignKey("Teacher.id"), nullable=False),
        sa.Column("substituteId", sa.String(),
                  sa.ForeignKey("Teacher.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("requestedAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolvedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )

    # ── Alert ─────────────────────────────────────────────────────────────
    op.create_table(
        "Alert",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("dutyId", sa.String(),
                  sa.ForeignKey("Duty.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── Absence ───────────────────────────────────────────────────────────
    op.create_table(
        "Absence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacherId", sa.String(),
                  sa.ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── AuditLog ──────────────────────────────────────────────────────────
    op.create_table(
        "AuditLog",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("details", sa.String(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── teacher_attendance (snake_case, added later by _run_column_migrations) ─
    op.create_table(
        "teacher_attendance",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("teacher_id", sa.String(),
                  sa.ForeignKey("Teacher.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("teacher_id", "date", name="uq_teacher_attendance_date"),
    )


def downgrade() -> None:
    # Reverse order so FKs unwind cleanly.
    op.drop_table("teacher_attendance")
    op.drop_table("AuditLog")
    op.drop_table("Absence")
    op.drop_table("Alert")
    op.drop_table("Substitution")
    op.drop_table("Lesson")
    op.drop_table("Duty")
    op.drop_table("Teacher")
    op.drop_table("User")
