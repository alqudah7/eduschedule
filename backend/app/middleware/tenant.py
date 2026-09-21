"""Tenant-scoped session context.

The DB session must have `app.current_school_id` set for the RLS
policy to allow reads/writes on tenant tables. This module wires a
per-request FastAPI dependency that:

  1. Reads the school_id claim from the current user's JWT.
  2. Sets `app.current_school_id` on the DB session using `SET LOCAL`
     (transactional — automatically resets at commit/rollback).
  3. Yields the session.

Any endpoint that touches tenant data must depend on `get_tenant_db`
instead of `get_db`. Endpoints that legitimately span tenants (rare)
depend on `get_admin_db` and MUST justify it in a comment.

Note on RLS enforcement in production:
FORCE ROW LEVEL SECURITY makes non-superuser table owners obey the
policy. However, if the app connects as a Postgres SUPERUSER (Railway's
default), the policy is bypassed for that role — RLS is then a
defense-in-depth layer that only bites when we run under a limited
role. Tightening this to a dedicated non-superuser role is filed as
follow-up work.
"""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import User


def _set_school_id(db: Session, school_id: int) -> None:
    """Apply the tenant GUC on this session.

    SET LOCAL is scoped to the surrounding transaction. FastAPI's session
    dependency yields a session that begins an implicit transaction on
    first use, so this GUC lives for the request and reverts on commit
    or close.
    """
    db.execute(text("SET LOCAL app.current_school_id = :sid"), {"sid": str(school_id)})


def get_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Iterator[Session]:
    """DB session with tenant isolation applied.

    Raises 403 if the current user has no school_id — should be
    impossible after Phase 1 backfill, but the check is here as a
    defense against a user row that predates the migration.
    """
    if current_user.school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no tenant assignment",
        )
    _set_school_id(db, current_user.school_id)
    yield db


def get_admin_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Iterator[Session]:
    """Escape hatch: cross-tenant DB session for platform-admin operations.

    Sets school_id to 0 which makes RLS reject all tenant rows — the
    caller MUST use the explicit `.no_tenant_filter()` method on
    tenant-scoped queries. This is deliberately awkward so admin bypass
    is greppable in code review.

    Only SUPER_ADMIN gets this. ORG_ADMIN is scoped to one organisation,
    which is NOT the same as "all schools" — the caller has to iterate
    org.schools themselves and set the tenant GUC per school if they
    want cross-school reads under an org. That's deliberate; unbounded
    cross-tenant reads should not be a one-liner even for org admins.
    """
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant DB scope requires SUPER_ADMIN role",
        )
    _set_school_id(db, 0)
    yield db
