"""composite indexes with school_id first

MULTITENANT.md §5 step 7. Every tenant lookup now filters by school_id
first — indexes must lead with school_id so RLS and app filters both
sit on a covering index.

We create new composite indexes but do NOT drop the pre-existing
single-column indexes yet. Reasons:
- Existing queries against email / teacher_id still benefit from them.
- Postgres will happily use the composite as a lookup on the leading
  column, so we can drop the singles later once we've measured actual
  query patterns under RLS.
- Keeping both means downgrade is a simple index drop — no need to
  re-create anything.

Revision ID: fa4c92e951a6
Revises: 3fb5bc61c3cb
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "fa4c92e951a6"
down_revision: Union[str, None] = "3fb5bc61c3cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table_name, columns) — Postgres identifier quoting handled
# per-name; table names use existing conventions.
NEW_INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_teacher_school_email",          '"Teacher"',        ["school_id", "email"]),
    ("ix_teacher_school_status",         '"Teacher"',        ["school_id", "status"]),
    ("ix_user_school_email",             '"User"',           ["school_id", "email"]),
    ("ix_lesson_school_teacher_day",     '"Lesson"',         ["school_id", '"teacherId"', "day"]),
    ("ix_lesson_school_day",             '"Lesson"',         ["school_id", "day"]),
    ("ix_duty_school_teacher_day",       '"Duty"',           ["school_id", '"teacherId"', "day"]),
    ("ix_duty_school_status",            '"Duty"',           ["school_id", "status"]),
    ("ix_substitution_school_absent",    '"Substitution"',   ["school_id", '"absentTeacherId"']),
    ("ix_substitution_school_substitute", '"Substitution"',  ["school_id", '"substituteId"']),
    ("ix_substitution_school_lesson",    '"Substitution"',   ["school_id", '"lessonId"']),
    ("ix_alert_school_created",          '"Alert"',          ["school_id", '"createdAt"']),
    ("ix_absence_school_teacher_date",   '"Absence"',        ["school_id", '"teacherId"', "date"]),
    ("ix_auditlog_school_created",       '"AuditLog"',       ["school_id", '"createdAt"']),
    ("ix_teacher_attendance_school_teacher_date",
                                          "teacher_attendance", ["school_id", "teacher_id", "date"]),
]


def upgrade() -> None:
    for name, tbl, cols in NEW_INDEXES:
        col_list = ", ".join(cols)
        op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {tbl} ({col_list})')


def downgrade() -> None:
    for name, _tbl, _cols in reversed(NEW_INDEXES):
        op.execute(f'DROP INDEX IF EXISTS {name}')
