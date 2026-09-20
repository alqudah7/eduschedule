"""backfill school_id to Al Hekma

MULTITENANT.md §5 step 4. Populates the freshly-added nullable
`school_id` column on every tenant table with Al Hekma's id.

Al Hekma is identified by slug `alhekma` rather than a hardcoded 1 —
if this migration runs on a database where the schools table has a
different auto-increment starting point (e.g. a restored dev copy),
the lookup still resolves correctly.

Downgrade sets school_id back to NULL. It does NOT drop the column —
that is the job of revision c3f705ecdedf's downgrade.

Revision ID: 887d83a51971
Revises: c3f705ecdedf
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "887d83a51971"
down_revision: Union[str, None] = "c3f705ecdedf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    conn = op.get_bind()
    school_row = conn.execute(sa.text(
        "SELECT id FROM schools WHERE slug = 'alhekma'"
    )).first()
    if not school_row:
        raise RuntimeError(
            "backfill: Al Hekma school not found. "
            "Ensure revision e2132b03e429 has run before this migration."
        )
    school_id = school_row.id

    for tbl in TENANT_TABLES:
        conn.execute(sa.text(
            f"UPDATE {tbl} SET school_id = :school_id WHERE school_id IS NULL"
        ), {"school_id": school_id})


def downgrade() -> None:
    conn = op.get_bind()
    for tbl in TENANT_TABLES:
        conn.execute(sa.text(f"UPDATE {tbl} SET school_id = NULL"))
