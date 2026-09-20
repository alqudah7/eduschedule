"""backfill must_change_password = TRUE for non-admin users

The 72 pre-existing teacher accounts still hold Teacher@123 (public
git history exposure) and the admin still holds Admin@123. This
revision forces every non-admin User to change their password on
next login. The admin account is intentionally excluded — the
operator rotates that one out of band; see OPS.md §5 / Batch 1
report.

Downgrade sets the flag back to FALSE for all rows to restore the
pre-revision state.

Revision ID: a27cce36aacd
Revises: cb4d0ec9c51b
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a27cce36aacd"
down_revision: Union[str, None] = "cb4d0ec9c51b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # role='ADMIN' is preserved because the operator handles that
    # account manually. Every other role — TEACHER, MANAGER, or any
    # future value — gets flagged.
    op.execute(
        'UPDATE "User" SET must_change_password = TRUE WHERE role != \'ADMIN\''
    )


def downgrade() -> None:
    op.execute('UPDATE "User" SET must_change_password = FALSE')
