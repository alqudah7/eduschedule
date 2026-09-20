"""find_user_for_login returns must_change_password

Extends the SECURITY DEFINER lookup so the login endpoint can decide
whether to route the user through the forced password-change flow
without an extra RLS-blocked SELECT against "User".

Return type changes, so a DROP + CREATE is required. Downgrade
restores the previous signature (id/email/password/name/role/school_id
only, from revision 12ce483c979f).

Revision ID: a84683bd9afe
Revises: a27cce36aacd
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a84683bd9afe"
down_revision: Union[str, None] = "a27cce36aacd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FUNCTION_UPGRADE = r"""
CREATE OR REPLACE FUNCTION public.find_user_for_login(
    _email text,
    _school_id integer
)
RETURNS TABLE (
    id text,
    email text,
    password text,
    name text,
    role text,
    school_id integer,
    must_change_password boolean
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $body$
    SELECT u.id, u.email, u.password, u.name, u.role, u.school_id,
           u.must_change_password
    FROM public."User" u
    WHERE u.email = _email
      AND u.school_id = _school_id
    LIMIT 1
$body$;
"""

_FUNCTION_DOWNGRADE = r"""
CREATE OR REPLACE FUNCTION public.find_user_for_login(
    _email text,
    _school_id integer
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
    # Return-type change requires a DROP first — CREATE OR REPLACE
    # cannot alter the RETURNS clause.
    op.execute("DROP FUNCTION IF EXISTS public.find_user_for_login(text, integer)")
    op.execute(sa.text(_FUNCTION_UPGRADE))
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
    op.execute("DROP FUNCTION IF EXISTS public.find_user_for_login(text, integer)")
    op.execute(sa.text(_FUNCTION_DOWNGRADE))
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
