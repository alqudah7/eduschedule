"""consolidate Absence into teacher_attendance

AUDIT #28 flagged Absence and TeacherAttendance as duplicate stores of
the same concept. Absence was the legacy table with 4 live rows in
production (per the row counts at the start of Batch 3).

Consolidation rules:
- For every row in Absence, upsert one row into teacher_attendance
  with status='absent'. The reason column becomes the note.
- ON CONFLICT (teacher_id, date) DO NOTHING — teacher_attendance is
  the more current store; if it already has a row for (teacher, date)
  its value is authoritative (the /attendance mark-absent flow is
  what runs day-to-day).
- After the copy, drop the Absence table.

Downgrade re-creates the Absence table with its original shape and
copies back every teacher_attendance row that has status='absent'.
The re-created rows lose the original Absence.id (a new cuid is
generated) and reason (mapped from note); production continues to
work either way because the endpoint that reads Absence has been
rewritten to read teacher_attendance directly.

Revision ID: 21c773d1e916
Revises: a84683bd9afe
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "21c773d1e916"
down_revision: Union[str, None] = "a84683bd9afe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO teacher_attendance (
            id, teacher_id, date, status, note,
            created_at, updated_at, school_id
        )
        SELECT
            a.id,
            a."teacherId",
            a.date::date,
            'absent',
            a.reason,
            a."createdAt",
            NULL,
            a.school_id
        FROM "Absence" a
        ON CONFLICT (teacher_id, date) DO NOTHING
        """
    )

    op.execute('DROP TABLE "Absence"')


def downgrade() -> None:
    # Recreate Absence with its original shape (pre-Alembic + Phase 1
    # school_id addition). Match the migration chain's expectations so
    # a future downgrade past the Phase 1 revisions does not blow up.
    op.execute(
        """
        CREATE TABLE "Absence" (
            id VARCHAR PRIMARY KEY,
            "teacherId" VARCHAR NOT NULL REFERENCES "Teacher"(id) ON DELETE CASCADE,
            date TIMESTAMP WITH TIME ZONE NOT NULL,
            reason VARCHAR,
            "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT now(),
            school_id INTEGER NOT NULL REFERENCES schools(id) ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        'ALTER TABLE "Absence" ENABLE ROW LEVEL SECURITY'
    )
    op.execute(
        'ALTER TABLE "Absence" FORCE ROW LEVEL SECURITY'
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON "Absence"
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
    op.execute(
        """
        INSERT INTO "Absence" (id, "teacherId", date, reason, "createdAt", school_id)
        SELECT
            'a-' || substr(md5(random()::text), 1, 22),
            ta.teacher_id,
            ta.date::timestamptz,
            ta.note,
            ta.created_at,
            ta.school_id
        FROM teacher_attendance ta
        WHERE ta.status = 'absent'
        """
    )
