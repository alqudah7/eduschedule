"""verify no nulls, set school_id NOT NULL

MULTITENANT.md §5 steps 5+6. Aborts if any tenant row still has a NULL
school_id — do not force NOT NULL over unmatched rows. Once verified,
each table gets ALTER COLUMN school_id SET NOT NULL applied.

Reversible: downgrade drops the NOT NULL back to nullable.

Revision ID: 3fb5bc61c3cb
Revises: 887d83a51971
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3fb5bc61c3cb"
down_revision: Union[str, None] = "887d83a51971"
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

    # Verify: find any table with rows that still have NULL school_id.
    unmatched: list[tuple[str, int]] = []
    for tbl in TENANT_TABLES:
        result = conn.execute(sa.text(
            f"SELECT COUNT(*) AS n FROM {tbl} WHERE school_id IS NULL"
        )).first()
        if result.n > 0:
            unmatched.append((tbl, result.n))

    if unmatched:
        summary = ", ".join(f"{t}={n}" for t, n in unmatched)
        raise RuntimeError(
            f"Refusing to enforce NOT NULL: unmatched rows remain — {summary}. "
            "Investigate and re-run the backfill (revision 887d83a51971) or "
            "delete orphan rows before rerunning this migration."
        )

    # All clean — enforce NOT NULL.
    for tbl in TENANT_TABLES:
        op.execute(sa.text(
            f"ALTER TABLE {tbl} ALTER COLUMN school_id SET NOT NULL"
        ))


def downgrade() -> None:
    for tbl in reversed(TENANT_TABLES):
        op.execute(sa.text(
            f"ALTER TABLE {tbl} ALTER COLUMN school_id DROP NOT NULL"
        ))
