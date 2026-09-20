"""hardened find_user_for_login SECURITY DEFINER function

Puts the login-lookup function into the migration chain. Previously it
existed only in production because it was applied by ad-hoc psql — a
restore from backup or a fresh dev database would produce a state where
nobody could log in.

Hardening compared to the ad-hoc version:

- `_school_id` is REQUIRED (no DEFAULT NULL). A caller can no longer
  request cross-tenant email matches by omitting the argument. The Python
  login endpoint now server-resolves the tenant and passes it in as a
  literal.
- `LIMIT 1` is defensive; combined with the (school_id, email) UNIQUE
  constraint from revision 8878824788ec there is at most one row, but the
  clamp survives future changes.
- `SET search_path = pg_catalog, public, pg_temp` — pg_catalog first so a
  hijacked search_path can't shadow "User" with a fake table.
- `REVOKE ALL FROM PUBLIC` before granting to eduschedule_app so a
  granted-to-PUBLIC default cannot leak the function.
- Function definer is whoever runs the migration (superuser). SECURITY
  DEFINER means executor still runs as owner — so the app role can call
  it but only through this narrow signature.

Role grant is conditional: on databases where the eduschedule_app role
has not yet been provisioned (ops step, documented in OPS.md), the
GRANT is skipped and the function is still created. It is safe to
re-run this revision to pick up the grant once the role exists.

Revision ID: 12ce483c979f
Revises: 28c532490174
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "12ce483c979f"
down_revision: Union[str, None] = "28c532490174"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FUNCTION_SQL = r"""
CREATE OR REPLACE FUNCTION public.find_user_for_login(
    _email text,
    _school_id integer      -- REQUIRED: no DEFAULT
)
RETURNS TABLE (
    id text,
    email text,
    password text,
    name text,
    role text,
    school_id integer
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $body$
    SELECT u.id, u.email, u.password, u.name, u.role, u.school_id
    FROM public."User" u
    WHERE u.email = _email
      AND u.school_id = _school_id
    LIMIT 1
$body$;
"""


def upgrade() -> None:
    # 1. Drop the prior (loose, DEFAULT NULL) signature if it exists — the
    #    new function has a different arity from what production carried, so
    #    CREATE OR REPLACE won't overwrite it.
    op.execute(
        "DROP FUNCTION IF EXISTS public.find_user_for_login(text, integer)"
    )
    op.execute("DROP FUNCTION IF EXISTS public.find_user_for_login(text)")

    # 2. Create hardened function.
    op.execute(sa.text(_FUNCTION_SQL))

    # 3. Lock down: revoke from PUBLIC, then grant to the app role IF it
    #    exists. Fresh DBs where ops hasn't yet created the role will still
    #    get the function; ops runs the GRANT manually or re-runs this
    #    migration once the role exists.
    op.execute(
        "REVOKE ALL ON FUNCTION public.find_user_for_login(text, integer) FROM PUBLIC"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'eduschedule_app') THEN
                EXECUTE 'GRANT EXECUTE ON FUNCTION public.find_user_for_login(text, integer) '
                        'TO eduschedule_app';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS public.find_user_for_login(text, integer)"
    )
