"""baseline

Represents the pre-Alembic production schema at the point Alembic was
introduced. Existing tables (User, Teacher, Lesson, Duty, Substitution,
Alert, Absence, AuditLog, teacher_attendance) were created via the
startup _run_column_migrations pattern; this baseline records that state
so subsequent revisions can layer on top.

Production is brought into sync with `alembic stamp 21b21e11f5af`.
Fresh databases can `alembic upgrade head` from empty — but they need
Base.metadata.create_all() to have run first (still driven by app.main
create_tables() until it can be retired).

Revision ID: 21b21e11f5af
Revises:
Create Date: 2026-09-20 10:34:56.533629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "21b21e11f5af"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally empty. Prod schema at this point exists via the legacy
    # startup migrations. See docstring above.
    pass


def downgrade() -> None:
    # No-op: this baseline never created anything to reverse.
    pass
