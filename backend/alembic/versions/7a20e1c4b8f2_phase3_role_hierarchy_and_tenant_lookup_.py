"""phase3 role hierarchy + tenant slug lookup

Revision ID: 7a20e1c4b8f2
Revises: 21c773d1e916
Create Date: 2026-09-21

Phase 3 (MULTITENANT.md) prep migration:

  1. Widen User.role to a four-level hierarchy — SUPER_ADMIN /
     ORG_ADMIN / SCHOOL_ADMIN / TEACHER — enforced by a CHECK
     constraint at the DB layer. Free-form strings were fine while
     "ADMIN" and "TEACHER" were the only values ever inserted; with a
     real second tenant we need a whitelist so a bug can't accidentally
     mint SUPERADMIN or Admin or "Super Admin" and slip past a role
     check that string-compares with != "SUPER_ADMIN".

     The existing 1 ADMIN row is migrated to SCHOOL_ADMIN — the same
     scope of authority it always had (one tenant). SUPER_ADMIN is
     introduced empty; there is no super-admin on production yet, and
     one gets provisioned out of band when we're ready to create the
     second tenant. Empty is the point: we don't want a live
     cross-tenant account existing before we intend to use it.

  2. Add a functional index on lower(schools.slug) — subdomain matching
     is case-insensitive (browsers lowercase the Host authority) and
     we don't want a seq scan on every login.

Reversible.
"""
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a20e1c4b8f2"
down_revision: Union[str, None] = "21c773d1e916"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


_ROLE_CHECK_NAME = "ck_user_role"
_ROLE_ALLOWED = ("SUPER_ADMIN", "ORG_ADMIN", "SCHOOL_ADMIN", "TEACHER")
_SLUG_LOWER_IDX = "ix_schools_slug_lower"


def upgrade() -> None:
    # 1. Migrate legacy ADMIN → SCHOOL_ADMIN before adding the CHECK
    #    (otherwise the constraint refuses to attach). The role a legacy
    #    ADMIN had was "admin of their one school" — SCHOOL_ADMIN is the
    #    faithful mapping. NEVER promote to SUPER_ADMIN implicitly; that
    #    is a manual, out-of-band grant.
    op.execute("""
        UPDATE "User" SET role = 'SCHOOL_ADMIN' WHERE role = 'ADMIN'
    """)

    # 2. Enforce the new whitelist. NOT VALID + VALIDATE two-step is not
    #    needed here because "User" is small (~80 rows on prod) and the
    #    scan is cheap. If this ever grows, split the CHECK addition
    #    into ADD ... NOT VALID + VALIDATE CONSTRAINT to avoid the
    #    exclusive lock on writes.
    allowed = ", ".join(f"'{r}'" for r in _ROLE_ALLOWED)
    op.execute(f"""
        ALTER TABLE "User"
        ADD CONSTRAINT {_ROLE_CHECK_NAME}
        CHECK (role IN ({allowed}))
    """)

    # 3. Functional lowercase index for subdomain lookups. Login and
    #    every tenant-resolved API request will run
    #    `SELECT ... FROM schools WHERE lower(slug) = lower($host_sub)`
    #    so the index has to be on the same expression.
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS {_SLUG_LOWER_IDX}
        ON schools (lower(slug))
    """)


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_SLUG_LOWER_IDX}")
    op.execute(f'ALTER TABLE "User" DROP CONSTRAINT IF EXISTS {_ROLE_CHECK_NAME}')
    # Reverse the legacy mapping. SCHOOL_ADMIN → ADMIN is only correct
    # if there were no NEW school_admins created after the upgrade —
    # this is the same load-bearing assumption every rename downgrade
    # carries. If new school_admins have appeared, downgrade should be
    # done manually.
    op.execute("""
        UPDATE "User" SET role = 'ADMIN' WHERE role = 'SCHOOL_ADMIN'
    """)
