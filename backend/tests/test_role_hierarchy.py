"""Role hierarchy sanity — pure Python, no DB required.

The live cross-tenant tests in test_multitenant_isolation.py exercise
the same code paths against a real Postgres, but this file is intended
to always run in CI so a rename of a role constant surfaces immediately.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
os.environ.setdefault("JWT_SECRET", "test")

import pytest
from fastapi import HTTPException

from app.middleware.auth import _ROLE_RANK, require_role
from app.models.teacher import User


def _user(role: str) -> User:
    return User(id="u", email="e", password="x", name="n",
                role=role, school_id=1)


def test_hierarchy_contains_exactly_four_ranks():
    assert set(_ROLE_RANK) == {
        "TEACHER", "SCHOOL_ADMIN", "ORG_ADMIN", "SUPER_ADMIN",
    }


def test_hierarchy_is_strictly_monotone():
    ranks = [_ROLE_RANK[r] for r in
             ("TEACHER", "SCHOOL_ADMIN", "ORG_ADMIN", "SUPER_ADMIN")]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)


@pytest.mark.parametrize("role", ["SCHOOL_ADMIN", "ORG_ADMIN", "SUPER_ADMIN"])
def test_require_school_admin_admits_higher_ranks(role):
    guard = require_role("SCHOOL_ADMIN")
    user = _user(role)
    assert guard(current_user=user) is user


def test_require_school_admin_denies_teacher():
    guard = require_role("SCHOOL_ADMIN")
    with pytest.raises(HTTPException) as exc:
        guard(current_user=_user("TEACHER"))
    assert exc.value.status_code == 403


def test_require_super_admin_denies_org_admin():
    """SUPER_ADMIN is the top of the hierarchy — no lower rank satisfies it."""
    guard = require_role("SUPER_ADMIN")
    for lower in ("TEACHER", "SCHOOL_ADMIN", "ORG_ADMIN"):
        with pytest.raises(HTTPException) as exc:
            guard(current_user=_user(lower))
        assert exc.value.status_code == 403


def test_unknown_role_treated_as_insufficient():
    """A stale row with a role that's not in the CHECK constraint list
    should be denied everywhere, not silently pass through."""
    guard = require_role("TEACHER")
    with pytest.raises(HTTPException):
        guard(current_user=_user("MYSTERY"))
