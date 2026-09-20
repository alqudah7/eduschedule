"""Explicit escape hatch for cross-tenant queries.

Rule: every SQLAlchemy query against a tenant-scoped model
(Teacher/User/Lesson/Duty/Substitution/Alert/AuditLog/
TeacherAttendance) MUST be filtered by ``school_id`` at the ORM
layer. RLS at the DB layer is the second line of defence; the ORM
filter is the first.

If a query LEGITIMATELY needs to see rows across every tenant
(the only current example is the seed function checking whether
any user exists at all before it bootstraps) it goes through this
helper.

Why a helper instead of just leaving the query bare:
- `grep -rn cross_tenant_query` returns the exact audit list of
  intentional bypasses. Reviewers should look at every hit.
- The ``reason`` argument forces the author to justify the bypass
  in code, not in a commit message that gets lost.
- If a bypass ever gets misused, the git blame is short.
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Query, Session


T = TypeVar("T")


def cross_tenant_query(db: Session, model: type[T], *, reason: str) -> "Query[T]":
    """Return an un-tenant-filtered query. Use only when strictly required.

    Args:
        db: SQLAlchemy session.
        model: Model class to query.
        reason: Human-readable justification for why this bypasses
            tenant scoping. Not optional. Grep-visible in the audit.
    """
    if not reason:
        raise ValueError("cross_tenant_query requires a non-empty `reason`")
    return db.query(model)
