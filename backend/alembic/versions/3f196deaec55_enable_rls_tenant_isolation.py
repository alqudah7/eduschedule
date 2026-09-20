"""enable row-level security with tenant_isolation policy

Phase 2, layer 1 of MULTITENANT.md §6. Enables RLS on every tenant-scoped
table and installs a policy that filters `school_id` against the DB-level
GUC `app.current_school_id`. The application sets this per request from
the JWT's school_id claim.

Policy semantics:
- If `app.current_school_id` is set, only rows matching are visible.
- If unset (or set to '0'), the policy evaluates to FALSE and NO rows
  are visible — a defensive default so an un-scoped request cannot leak.

FORCE ROW LEVEL SECURITY is set so table owners (which our app user is
typically NOT — Railway uses a superuser) also have to obey the policy.
Without FORCE, superuser sees everything and RLS is silently bypassed.

Downgrade drops the policy and disables RLS.

Revision ID: 3f196deaec55
Revises: 8878824788ec
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "3f196deaec55"
down_revision: Union[str, None] = "8878824788ec"
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

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    for tbl in TENANT_TABLES:
        # Enable + FORCE so table owners obey the policy too.
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")

        # NULLIF+coalesce trick: if the GUC isn't set the setting returns ''
        # (empty string), NULLIF('', '') is NULL, coalesce to '0', which
        # then compares against school_id and matches nothing.
        op.execute(
            f"""
            CREATE POLICY {POLICY_NAME} ON {tbl}
            USING (
                school_id = NULLIF(
                    coalesce(current_setting('app.current_school_id', true), '0'),
                    ''
                )::integer
            )
            WITH CHECK (
                school_id = NULLIF(
                    coalesce(current_setting('app.current_school_id', true), '0'),
                    ''
                )::integer
            )
            """
        )


def downgrade() -> None:
    for tbl in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
