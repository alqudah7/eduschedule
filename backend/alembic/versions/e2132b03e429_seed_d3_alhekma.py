"""seed d3 org + al hekma school + school_settings

Data migration. Creates:
  - organization "D3 Consultants" (slug d3)
  - school "Al Hekma International School" (slug alhekma,
    tz Asia/Bahrain, locale EN)
  - school_settings row per MULTITENANT.md §3

Downgrade removes those exact rows so this is safely reversible in
isolation; downstream migrations that add school_id to tenant tables
assume the Al Hekma row exists, so downgrade order must be respected.

Revision ID: e2132b03e429
Revises: ac08810385eb
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2132b03e429"
down_revision: Union[str, None] = "ac08810385eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Organization: D3 Consultants
    org_result = conn.execute(sa.text("""
        INSERT INTO organizations (name, slug, country, plan, status)
        VALUES (:name, :slug, :country, 'STANDARD', 'ACTIVE')
        RETURNING id
    """), {"name": "D3 Consultants", "slug": "d3", "country": "BH"})
    org_id = org_result.scalar_one()

    # 2. School: Al Hekma International School
    school_result = conn.execute(sa.text("""
        INSERT INTO schools (
            organization_id, name, slug, country, timezone,
            locale_default, status
        )
        VALUES (
            :org_id, :name, :slug, :country, :timezone,
            'EN', 'ACTIVE'
        )
        RETURNING id
    """), {
        "org_id": org_id,
        "name": "Al Hekma International School",
        "slug": "alhekma",
        "country": "BH",
        "timezone": "Asia/Bahrain",
    })
    school_id = school_result.scalar_one()

    # 3. school_settings per MULTITENANT.md §3.
    # `CAST(:x AS type)` is used instead of `:x::type` because psycopg2's
    # named-param translator gets confused by the `::` which is also
    # Postgres's shorthand cast operator.
    conn.execute(sa.text("""
        INSERT INTO school_settings (
            school_id, working_days, school_levels, supported_locales,
            periods, breaks, features_enabled
        )
        VALUES (
            :school_id,
            CAST(:working_days AS text[]),
            CAST(:school_levels AS text[]),
            CAST(:supported_locales AS text[]),
            CAST(:periods AS jsonb),
            CAST(:breaks AS jsonb),
            CAST(:features_enabled AS jsonb)
        )
    """), {
        "school_id": school_id,
        "working_days": "{SUN,MON,TUE,WED,THU}",
        "school_levels": "{PRESCHOOL,ELEMENTARY,MIDDLE,HIGH}",
        "supported_locales": "{EN,AR}",
        "periods": (
            '[{"number":1,"label":"Period 1","start":"07:40","end":"08:30"},'
            '{"number":2,"label":"Period 2","start":"09:00","end":"09:50"},'
            '{"number":3,"label":"Period 3","start":"09:50","end":"10:40"},'
            '{"number":4,"label":"Period 4","start":"10:40","end":"11:30"},'
            '{"number":5,"label":"Period 5","start":"11:50","end":"12:40"},'
            '{"number":6,"label":"Period 6","start":"12:40","end":"13:30"}]'
        ),
        "breaks": (
            '[{"label":"Morning","start":"08:30","end":"09:00"},'
            '{"label":"Midday","start":"11:30","end":"11:50"}]'
        ),
        "features_enabled": "{}",
    })


def downgrade() -> None:
    conn = op.get_bind()
    # Cascade from schools -> school_settings via FK ondelete=CASCADE.
    conn.execute(sa.text("DELETE FROM schools WHERE slug = :s"), {"s": "alhekma"})
    conn.execute(sa.text("DELETE FROM organizations WHERE slug = :s"), {"s": "d3"})
