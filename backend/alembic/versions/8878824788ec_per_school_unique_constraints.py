"""per-school unique constraints

MULTITENANT.md §5 step 8. Global uniqueness of email and other keys is
wrong under multi-tenancy — one email may exist across two schools.

Changes:
    User.email:  UNIQUE (email) -> UNIQUE (school_id, email)
    Teacher.email: UNIQUE (email) -> UNIQUE (school_id, email)

Substitution.dutyId already has a per-duty UNIQUE (dutyId) that is fine
as-is: a Duty is scoped to one school so its uniqueness is implicitly
per-school. Adding school_id to that constraint would be a lie about
what's being enforced.

Downgrade restores the global constraints.

Revision ID: 8878824788ec
Revises: fa4c92e951a6
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "8878824788ec"
down_revision: Union[str, None] = "fa4c92e951a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User.email: drop global, add composite.
    # The existing global constraint was auto-named "User_email_key" by
    # Postgres. It might also be present as a unique INDEX with the same
    # name depending on how it was created — DROP CONSTRAINT is safest.
    op.execute('ALTER TABLE "User" DROP CONSTRAINT IF EXISTS "User_email_key"')
    op.execute(
        'ALTER TABLE "User" ADD CONSTRAINT uq_user_school_email '
        'UNIQUE (school_id, email)'
    )

    op.execute('ALTER TABLE "Teacher" DROP CONSTRAINT IF EXISTS "Teacher_email_key"')
    op.execute(
        'ALTER TABLE "Teacher" ADD CONSTRAINT uq_teacher_school_email '
        'UNIQUE (school_id, email)'
    )


def downgrade() -> None:
    op.execute('ALTER TABLE "Teacher" DROP CONSTRAINT IF EXISTS uq_teacher_school_email')
    op.execute(
        'ALTER TABLE "Teacher" ADD CONSTRAINT "Teacher_email_key" UNIQUE (email)'
    )
    op.execute('ALTER TABLE "User" DROP CONSTRAINT IF EXISTS uq_user_school_email')
    op.execute(
        'ALTER TABLE "User" ADD CONSTRAINT "User_email_key" UNIQUE (email)'
    )
