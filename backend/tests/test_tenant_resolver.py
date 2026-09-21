"""Unit tests for the Phase 3 tenant resolver.

Pure — no DB, no HTTP. Exercises the header parsing surface directly
so a future refactor cannot regress unknown-subdomain handling, the
reserved list, or the Origin/Referer/Host precedence order.

The DB-hitting variant lives in test_multitenant_isolation.py, which
covers the "unknown slug → 404 UNKNOWN_TENANT" end-to-end path.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
os.environ.setdefault("JWT_SECRET", "test")

import pytest

from starlette.datastructures import Headers
from starlette.requests import Request

from app.services import tenant_resolver as tr


def _make_request(**headers) -> Request:
    """Build a lightweight Starlette Request with just the headers set.

    We only touch request.headers in the resolver so a full ASGI scope
    isn't required — a partial dict is enough.
    """
    header_list = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "headers": header_list,
        "method": "POST",
        "path": "/api/auth/login",
    }
    return Request(scope=scope)


# ── _extract_subdomain ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "host,parent,expected",
    [
        ("alhekma.eduschedule.app",     ".eduschedule.app", "alhekma"),
        ("SUNRISE.eduschedule.app",     ".eduschedule.app", "sunrise"),
        ("alhekma.eduschedule.app:443", ".eduschedule.app", None),   # port not stripped here — that's _strip_port's job
        ("eduschedule.app",             ".eduschedule.app", None),   # apex — no tenant
        ("a.b.eduschedule.app",         ".eduschedule.app", None),   # nested — outside wildcard cert
        ("attacker.com",                ".eduschedule.app", None),   # wrong parent
        ("www.eduschedule.app",         ".eduschedule.app", None),   # reserved
        ("api.eduschedule.app",         ".eduschedule.app", None),   # reserved
        ("admin.eduschedule.app",       ".eduschedule.app", None),   # reserved
    ],
)
def test_extract_subdomain(host, parent, expected):
    assert tr._extract_subdomain(host, parent) == expected


# ── header URL parsing ───────────────────────────────────────────────────


def test_slug_from_origin_extracts_from_full_url():
    slug = tr._slug_from_header_url(
        "https://alhekma.eduschedule.app", ".eduschedule.app",
    )
    assert slug == "alhekma"


def test_slug_from_origin_ignores_wrong_domain():
    assert tr._slug_from_header_url(
        "https://alhekma.attacker.com", ".eduschedule.app",
    ) is None


def test_slug_from_origin_survives_malformed_input():
    assert tr._slug_from_header_url("", ".eduschedule.app") is None
    assert tr._slug_from_header_url("not a url", ".eduschedule.app") is None


# ── resolve_tenant_slug precedence ──────────────────────────────────────────


def test_origin_beats_referer(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(
        origin="https://alhekma.eduschedule.app",
        referer="https://sunrise.eduschedule.app/dashboard",
    )
    assert tr.resolve_tenant_slug(req) == "alhekma"


def test_referer_when_no_origin(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(referer="https://sunrise.eduschedule.app/login")
    assert tr.resolve_tenant_slug(req) == "sunrise"


def test_host_fallback_when_api_under_wildcard(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(host="alhekma-api.eduschedule.app")
    assert tr.resolve_tenant_slug(req) == "alhekma-api"


def test_x_tenant_slug_header_blocked_in_prod(monkeypatch):
    """The dev/test header must not be honoured with the flag off."""
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(**{"x-tenant-slug": "sunrise"})
    assert tr.resolve_tenant_slug(req) is None


def test_x_tenant_slug_header_honoured_with_flag(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", True)
    req = _make_request(**{"x-tenant-slug": "SUNRISE"})
    assert tr.resolve_tenant_slug(req) == "sunrise"  # lowercased


def test_default_tenant_slug_bridges_single_alias(monkeypatch):
    """During the pre-wildcard-DNS period, a request with no discoverable
    tenant identity falls through to the configured default so existing
    single-alias prod keeps working."""
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(host="eduschedule-api-production.up.railway.app")
    assert tr.resolve_tenant_slug(req) == "alhekma"


def test_unresolved_when_default_is_empty(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(host="eduschedule-api-production.up.railway.app")
    assert tr.resolve_tenant_slug(req) is None


def test_reserved_subdomain_falls_through_not_accepted(monkeypatch):
    """A visit to www.eduschedule.app / api.eduschedule.app / apex must
    NOT be treated as a tenant lookup for slug 'www'/'api' — those are
    reserved. When no default is configured this returns None (404 at
    the DB-hitting layer)."""
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(origin="https://www.eduschedule.app")
    assert tr.resolve_tenant_slug(req) is None


# ── header-only variant does NOT fall back to DEFAULT_TENANT_SLUG ──────────


def test_headers_only_variant_ignores_default(monkeypatch):
    """resolve_tenant_slug_from_headers must never fall through to
    DEFAULT_TENANT_SLUG — a post-login curl caller has no Origin, and
    the JWT-vs-Origin check would 403 them if the default kicked in."""
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)

    req = _make_request(host="eduschedule-api-production.up.railway.app")
    # resolve_tenant_slug (full) → alhekma via DEFAULT fallback
    assert tr.resolve_tenant_slug(req) == "alhekma"
    # resolve_tenant_slug_from_headers (strict) → None
    assert tr.resolve_tenant_slug_from_headers(req) is None


def test_headers_only_variant_honours_origin(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)
    req = _make_request(origin="https://sunrise.eduschedule.app")
    # DEFAULT is alhekma but the request's Origin says sunrise — Origin wins.
    assert tr.resolve_tenant_slug_from_headers(req) == "sunrise"


# ── enforce_tenant_matches_jwt (unit — DB lookup mocked) ───────────────────


class _StubResult:
    """Chainable stub for `db.execute(...).mappings().first()`."""

    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _StubDB:
    """Minimal SQLAlchemy Session stand-in for the resolver's DB lookup.

    Returns a fake row for known slugs, None otherwise. This isolates
    the enforce_tenant_matches_jwt logic from a live DB dependency.
    """

    def __init__(self, tenants_by_slug):
        self._by_slug = tenants_by_slug

    def execute(self, sql, params):
        slug = params["slug"].lower()
        return _StubResult(self._by_slug.get(slug))


def test_enforce_no_op_when_headers_absent(monkeypatch):
    """A curl caller with no Origin/Referer/Host-in-wildcard and
    ALLOW_TENANT_HEADER=false must be admitted — the check should not
    invent a tenant identity for them."""
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)

    req = _make_request(host="eduschedule-api-production.up.railway.app")
    stub = _StubDB({"alhekma": {"id": 1, "slug": "alhekma", "name": "Al Hekma"}})
    # No exception raised → pass.
    tr.enforce_tenant_matches_jwt(req, stub, jwt_school_id=1)


def test_enforce_passes_when_origin_matches_jwt(monkeypatch):
    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)

    req = _make_request(origin="https://alhekma.eduschedule.app")
    stub = _StubDB({"alhekma": {"id": 1, "slug": "alhekma", "name": "Al Hekma"}})
    tr.enforce_tenant_matches_jwt(req, stub, jwt_school_id=1)


def test_enforce_403_when_origin_disagrees_with_jwt(monkeypatch):
    """The headline test: valid Al Hekma JWT (school_id=1) + Origin for
    Sunrise (id=2) → 403 TENANT_JWT_MISMATCH."""
    from fastapi import HTTPException

    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)

    req = _make_request(origin="https://sunrise.eduschedule.app")
    stub = _StubDB({
        "alhekma": {"id": 1, "slug": "alhekma", "name": "Al Hekma"},
        "sunrise": {"id": 2, "slug": "sunrise", "name": "Sunrise"},
    })
    with pytest.raises(HTTPException) as exc:
        tr.enforce_tenant_matches_jwt(req, stub, jwt_school_id=1)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "TENANT_JWT_MISMATCH"


def test_enforce_403_when_origin_names_unknown_school(monkeypatch):
    """Valid JWT + Origin for a subdomain that doesn't map to any school
    must NOT be admitted — it's either a bug (frontend on a stale host)
    or a probe. Same 403 code so an attacker can't distinguish."""
    from fastapi import HTTPException

    monkeypatch.setattr(tr.settings, "TENANT_PARENT_DOMAIN", ".eduschedule.app")
    monkeypatch.setattr(tr.settings, "DEFAULT_TENANT_SLUG", "alhekma")
    monkeypatch.setattr(tr.settings, "ALLOW_TENANT_HEADER", False)

    req = _make_request(origin="https://nothere.eduschedule.app")
    stub = _StubDB({"alhekma": {"id": 1, "slug": "alhekma", "name": "Al Hekma"}})
    with pytest.raises(HTTPException) as exc:
        tr.enforce_tenant_matches_jwt(req, stub, jwt_school_id=1)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "TENANT_JWT_MISMATCH"
