"""add nullable school_id to tenant tables

MULTITENANT.md §5 step 3. Adds `school_id INTEGER NULL REFERENCES
schools(id)` to all nine tenant-scoped tables so that the next revision
can backfill. Keeping this separate from the backfill and the NOT NULL
enforcement lets each step be rolled back on its own.

Tables (per §1):
    "Teacher" · "User" · "Lesson" · "Duty" · "Substitution"
    "Alert" · "Absence" · "AuditLog" · teacher_attendance

Table names in the current schema are Pascal-quoted for everything
except teacher_attendance (which was created later via raw SQL and
never renamed). Both conventions are preserved.

Revision ID: c3f705ecdedf
Revises: e2132b03e429
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f705ecdedf"
down_revision: Union[str, None] = "e2132b03e429"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Order matters only for FK direction. All FKs point at schools.id which
# already exists at this point.
TENANT_TABLES: list[str] = [
    '"Teacher"',
    '"User"',
    '"Lesson"',
    '"Duty"',
    '"Substitution"',
    '"Alert"',
    '"Absence"',
    '"AuditLog"',
    "teacher_attendance",
]


def upgrade() -> None:
    for tbl in TENANT_TABLES:
        op.execute(sa.text(
            f'ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS school_id INTEGER '
            f'REFERENCES schools(id) ON DELETE RESTRICT'
        ))


def downgrade() -> None:
    for tbl in reversed(TENANT_TABLES):
        op.execute(sa.text(f'ALTER TABLE {tbl} DROP COLUMN IF EXISTS school_id'))
