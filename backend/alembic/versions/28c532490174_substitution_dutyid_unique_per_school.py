"""Substitution.dutyId unique constraint now includes school_id

Previous state: UNIQUE (dutyId). "Implicitly scoped per school because
Duty is per-school" — true until someone changes Duty. Under-defended
by design.

New state: UNIQUE (school_id, dutyId). Explicit. If Duty ever gets
denormalised or cross-school linkage happens, the constraint continues
to prevent duplicate Substitution rows against the same duty from
different schools.

Idempotency detail: the original UNIQUE was inline on the column
definition and Postgres auto-named it "Substitution_dutyId_key". IF
EXISTS handles the case where it may already have been renamed or
dropped.

Revision ID: 28c532490174
Revises: 3f196deaec55
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "28c532490174"
down_revision: Union[str, None] = "3f196deaec55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE "Substitution" DROP CONSTRAINT IF EXISTS "Substitution_dutyId_key"')
    op.execute(
        'ALTER TABLE "Substitution" '
        'ADD CONSTRAINT uq_substitution_school_duty '
        'UNIQUE (school_id, "dutyId")'
    )


def downgrade() -> None:
    op.execute('ALTER TABLE "Substitution" DROP CONSTRAINT IF EXISTS uq_substitution_school_duty')
    op.execute(
        'ALTER TABLE "Substitution" '
        'ADD CONSTRAINT "Substitution_dutyId_key" UNIQUE ("dutyId")'
    )
