"""Server-side tenant resolution.

Phase 3 removes the `_LOGIN_SCHOOL_ID = 1` hardcode in favour of a
resolver that maps the request's public origin (Host / Referer /
Origin) onto a `schools` row. The point of the exercise is that a
client cannot influence which tenant they authenticate against by
tampering with a request body field — the tenant is derived from
how they got here.

The tricky detail is that our API and our web app live on different
hostnames:

    web  :  <slug>.<tenant-parent-domain>          (Vercel, wildcard cert)
    api  :  eduschedule-api-production.up.railway.app   (Railway, fixed host)

Meaning the API's own Host header is useless as a tenant identity.
What DOES travel to the API is:

  * Origin  — set by the browser on every fetch(); cannot be spoofed
              from JS running under a different origin (SOP).
  * Referer — same guarantee, weaker (can be stripped).
  * X-Tenant-Slug — an explicit header we accept ONLY when
              ``settings.ALLOW_TENANT_HEADER`` is true (local dev,
              test runs, curl). Never in production.

Resolution order:
  1. Origin header, parsed for the subdomain against
     ``settings.TENANT_PARENT_DOMAIN`` (e.g. ``.eduschedule.app``).
  2. Referer header, same treatment.
  3. Host header — used only when the API itself is under the
     tenant-parent-domain wildcard (future: ``<slug>-api.eduschedule.app``).
     Not the case today, so this branch is inert on prod but useful
     for the second-tenant integration test.
  4. X-Tenant-Slug header — dev/test only, gated on the flag above.
  5. ``settings.DEFAULT_TENANT_SLUG`` — the bridge for the current
     single-alias prod deploy where no wildcard exists yet.

Unknown subdomain / no resolvable slug → 404 with a stable error code
so the frontend can show a "no such school" page instead of a raw 500.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db


# The slug we consider "not a tenant subdomain" — apex/www/api don't
# resolve to a school, they resolve to marketing / gateway pages.
_RESERVED_SUBDOMAINS = frozenset({"www", "api", "admin", "app", "docs", "status"})


@dataclass(frozen=True)
class ResolvedTenant:
    """The tenant a request was made under.

    Immutable so downstream code cannot accidentally reassign it — the
    tenant is fixed for the lifetime of the request.
    """

    id: int
    slug: str
    name: str


def _strip_port(host_authority: str) -> str:
    # "alhekma.eduschedule.app:8080" → "alhekma.eduschedule.app"
    return host_authority.split(":", 1)[0].lower().strip(".")


def _extract_subdomain(host: str, parent_domain: str) -> Optional[str]:
    """If ``host`` sits under ``parent_domain``, return the leftmost label.

    ``parent_domain`` is written with a leading dot in config (``.eduschedule.app``)
    so we can distinguish ``eduschedule.app`` (apex, no tenant) from
    ``alhekma.eduschedule.app`` (leftmost label = "alhekma").
    """
    parent = parent_domain.lstrip(".").lower()
    host = host.lower()
    if not host.endswith("." + parent):
        return None
    label = host[: -(len(parent) + 1)]
    # Reject nested subdomains like a.b.eduschedule.app — the wildcard
    # cert only covers one level and misuse could leak requests to a
    # tenant that doesn't exist.
    if "." in label or not label:
        return None
    if label in _RESERVED_SUBDOMAINS:
        return None
    return label


def _slug_from_header_url(header_value: str, parent_domain: str) -> Optional[str]:
    """Origin/Referer parse. Returns None on any parse failure — no
    exceptions bubble up from a malformed header."""
    if not header_value:
        return None
    try:
        parsed = urlparse(header_value)
    except ValueError:
        return None
    if not parsed.hostname:
        return None
    return _extract_subdomain(parsed.hostname, parent_domain)


def _lookup_tenant(db: Session, slug: str) -> Optional[ResolvedTenant]:
    """Case-insensitive slug lookup.

    Login-eligible statuses are the ones on the schools CHECK constraint
    minus SUSPENDED — flipping a tenant to SUSPENDED is our quarantine
    lever and takes effect without a redeploy. TRIAL is a normal working
    state for newly-provisioned schools and MUST authenticate; the
    previous version excluded TRIAL and locked new tenants out.

    Soft-deleted rows are always rejected.
    """
    from sqlalchemy import text

    row = db.execute(
        text(
            """
            SELECT id, slug, name
            FROM schools
            WHERE lower(slug) = lower(:slug)
              AND status IN ('ACTIVE', 'TRIAL')
              AND deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"slug": slug},
    ).mappings().first()
    if not row:
        return None
    return ResolvedTenant(id=row["id"], slug=row["slug"], name=row["name"])


def resolve_tenant_slug_from_headers(request: Request) -> Optional[str]:
    """Header-only slug resolution — never falls through to DEFAULT_TENANT_SLUG.

    Used post-login by ``get_current_user`` to detect JWT-vs-Origin
    disagreement. A curl caller with no Origin/Referer/Host-in-wildcard
    and ALLOW_TENANT_HEADER=false returns None, and the caller does
    NOT reject the request (they must be a non-browser client).
    Silence here is different from "no such tenant".
    """
    parent = settings.TENANT_PARENT_DOMAIN

    # 1. Origin — browser-set, SOP-protected on fetch/XHR
    slug = _slug_from_header_url(request.headers.get("origin", ""), parent)
    if slug:
        return slug

    # 2. Referer — same treatment, second choice because it can be
    #    stripped by referrer-policy.
    slug = _slug_from_header_url(request.headers.get("referer", ""), parent)
    if slug:
        return slug

    # 3. Host — only interesting if the API itself is on the wildcard
    #    (deferred DNS story). Cheap check, safe to leave in.
    host = _strip_port(request.headers.get("host", ""))
    slug = _extract_subdomain(host, parent)
    if slug:
        return slug

    # 4. X-Tenant-Slug — dev/test override. Guarded so a prod deploy
    #    that accidentally sets ALLOW_TENANT_HEADER=true is the whole
    #    problem, not the presence of the branch.
    if settings.ALLOW_TENANT_HEADER:
        header_slug = request.headers.get("x-tenant-slug", "").strip().lower()
        if header_slug:
            return header_slug

    return None


def resolve_tenant_slug(request: Request) -> Optional[str]:
    """Header-based slug with a DEFAULT_TENANT_SLUG fallback.

    Used pre-login (get_current_tenant) so single-alias production keeps
    working while wildcard DNS is deferred. Post-login checks MUST use
    resolve_tenant_slug_from_headers instead — falling back to a default
    at that layer would 403 legitimate non-browser callers.
    """
    slug = resolve_tenant_slug_from_headers(request)
    if slug:
        return slug

    # Default tenant — the bridge until wildcard DNS lands. On
    # single-alias prod (eduschedulealhekma.vercel.app → Al Hekma),
    # this is what keeps existing logins working. Empty string
    # means "no default configured" and forces unknown-tenant 404.
    if settings.DEFAULT_TENANT_SLUG:
        return settings.DEFAULT_TENANT_SLUG.strip().lower()

    return None


def enforce_tenant_matches_jwt(request: Request, db, jwt_school_id: int) -> None:
    """Post-login check: if the request carries a discoverable tenant
    identity (Origin / Referer / Host-in-wildcard / dev-only header) AND
    it disagrees with the JWT's school_id claim, reject with 403.

    - No Origin/Referer/Host resolvable → do nothing. curl and mobile
      clients don't send Origin, and we don't want to break them.
    - DEFAULT_TENANT_SLUG is deliberately NOT consulted here; it's a
      pre-login bridge, not an authoritative post-login source.
    - Unknown slug (resolves to a name but the school doesn't exist)
      → 403 as well. A JWT holder pointing at a bogus subdomain is
      either misconfigured or probing, both worth surfacing.

    JWT is authoritative for tenant identity once issued. This function
    ONLY catches the disagreement case — the JWT's school_id itself is
    verified against the persisted User.school_id one layer up.
    """
    slug = resolve_tenant_slug_from_headers(request)
    if slug is None:
        # Non-browser client or trusted single-alias caller. Nothing
        # to compare against.
        return

    tenant = _lookup_tenant(db, slug)
    if tenant is None or tenant.id != jwt_school_id:
        # Either "tenant doesn't exist" or "tenant exists but is not
        # yours". Same response either way — no information leak about
        # which of the two it is.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TENANT_JWT_MISMATCH",
                "message": (
                    "The tenant identified by this request's origin does not "
                    "match the tenant your session was issued for. Log in "
                    "again from the correct subdomain."
                ),
            },
        )


def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> ResolvedTenant:
    """FastAPI dependency: return the tenant for this request, or 404.

    The 404 payload includes ``code=UNKNOWN_TENANT`` so the frontend can
    switch to the "school not set up" page without brittle string
    matching on the human-readable detail.
    """
    slug = resolve_tenant_slug(request)
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "UNKNOWN_TENANT",
                    "message": "This subdomain is not associated with a school."},
        )

    tenant = _lookup_tenant(db, slug)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "UNKNOWN_TENANT",
                    "message": "This subdomain is not associated with a school."},
        )
    return tenant
