"""add must_change_password column on User

Adds a boolean flag the login endpoint consults to force a password
change on next login. Server default is FALSE so existing rows pick
up a sane value; the following revision backfills TRUE for accounts
that need it.

Revision ID: cb4d0ec9c51b
Revises: 12ce483c979f
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cb4d0ec9c51b"
down_revision: Union[str, None] = "12ce483c979f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "User",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("User", "must_change_password")
