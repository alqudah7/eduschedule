"""SUPER_ADMIN endpoints — cross-tenant platform administration.

Every route in here is gated on the SUPER_ADMIN role and every
mutating action lands in the AFFECTED school's AuditLog (not a
global platform log — see MULTITENANT.md §7).

Kept small on purpose. If Phase 3 grows more admin surface, split
this file by resource; but a fat "admin.py" that touches all
resources is worse than a small one.
"""
from __future__ import annotations

import re
import secrets
from typing import Optional

import cuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, constr
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import (
    get_current_user, hash_password, require_super_admin,
)
from app.middleware.tenant import get_admin_db
from app.models.teacher import User
from app.models.tenant import Organization, School
from app.utils.audit import write_audit_log
from app.utils.email_domains import (
    PlaceholderDomainError, assert_domain_usable_for_admin,
)

router = APIRouter()


_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")


class _CreateSchoolBody(BaseModel):
    """Create a new tenant.

    ``slug`` is what winds up as the DNS-visible subdomain. Kept to
    lowercase alphanumerics + hyphen so we don't have to worry about
    IDN, punycode, or reserved characters in the wildcard.
    """
    organization_slug: constr(min_length=1, max_length=32) = Field(  # type: ignore[valid-type]
        ..., description="Existing organization slug to attach to")
    name: constr(min_length=1, max_length=200) = Field(...)  # type: ignore[valid-type]
    slug: constr(min_length=1, max_length=32) = Field(...)  # type: ignore[valid-type]
    country: Optional[str] = None
    timezone: str = "UTC"
    locale_default: str = "EN"
    admin_email: str = Field(..., description="First SCHOOL_ADMIN for the tenant")


class _CreateOrgBody(BaseModel):
    name: constr(min_length=1, max_length=200) = Field(...)  # type: ignore[valid-type]
    slug: constr(min_length=1, max_length=32) = Field(...)  # type: ignore[valid-type]
    country: Optional[str] = None


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_SLUG",
                "message": ("Slug must be lowercase alphanumeric + hyphen, "
                            "1-32 chars, no leading/trailing hyphen."),
            },
        )


@router.post("/organizations", status_code=201)
def create_organization(
    body: _CreateOrgBody,
    db: Session = Depends(get_admin_db),
    current_user: User = Depends(require_super_admin),
):
    """Create a new customer organisation. Only orgs group schools."""
    _validate_slug(body.slug)
    org = Organization(
        name=body.name, slug=body.slug, country=body.country,
        plan="TRIAL", status="ACTIVE",
    )
    db.add(org)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ORG_SLUG_TAKEN", "message": "Slug already in use"},
        )
    db.refresh(org)
    return {"id": org.id, "slug": org.slug, "name": org.name}


@router.post("/schools", status_code=201)
def create_school(
    body: _CreateSchoolBody,
    db: Session = Depends(get_admin_db),
    current_user: User = Depends(require_super_admin),
):
    """Provision a tenant. Creates the school row, its default settings,
    a bootstrap SCHOOL_ADMIN, and writes the creation event to the NEW
    school's AuditLog (so the tenant sees their own provisioning history
    once they log in).

    Returns the initial password out-of-band in the response — this is a
    super-admin-only endpoint, and the response body is the SUPER_ADMIN's
    only path to the credential. It is NOT stored in plaintext.
    """
    _validate_slug(body.slug)

    # Placeholder-domain guard. Convention: every school's SCHOOL_ADMIN
    # uses that school's own work email — no example.com, no
    # eduschedule.com seed-demo carryovers, no *.test/*.example RFC-
    # reserved TLDs. Fail before we open the transaction so we don't
    # have to unwind a partial provision.
    try:
        assert_domain_usable_for_admin(body.admin_email)
    except PlaceholderDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "PLACEHOLDER_ADMIN_DOMAIN",
                    "domain": exc.domain, "message": exc.reason},
        )

    org = db.query(Organization).filter(
        Organization.slug == body.organization_slug,
    ).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORG_NOT_FOUND", "message": "Organization not found"},
        )

    # Slug uniqueness is enforced by uq_schools_slug; catch and translate
    # the IntegrityError so callers get a stable, translatable code.
    existing = db.query(School).filter(School.slug == body.slug).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SCHOOL_SLUG_TAKEN", "message": "Slug already in use"},
        )

    new_school = School(
        organization_id=org.id, name=body.name, slug=body.slug,
        country=body.country, timezone=body.timezone,
        locale_default=body.locale_default, status="TRIAL",
    )
    db.add(new_school)
    db.flush()  # need new_school.id for the audit log and the admin user

    # Default school settings — minimal viable set so the tenant can
    # exercise the app immediately. Callers can PATCH later.
    db.execute(text("""
        INSERT INTO school_settings
        (school_id, working_days, school_levels, supported_locales,
         periods, breaks, grade_labels, features_enabled)
        VALUES (:sid,
                ARRAY['SUN','MON','TUE','WED','THU'],
                ARRAY['ELEMENTARY','MIDDLE','HIGH'],
                ARRAY['EN'],
                '[]'::jsonb, '[]'::jsonb, NULL, '{}'::jsonb)
    """), {"sid": new_school.id})

    # Bootstrap SCHOOL_ADMIN — random password, must_change_password=TRUE
    # so their first API call bounces them to /change-password.
    bootstrap_pw = secrets.token_urlsafe(16)
    admin_user = User(
        id=cuid.cuid(),
        email=body.admin_email,
        password=hash_password(bootstrap_pw),
        name=f"{body.name} Admin",
        role="SCHOOL_ADMIN",
        school_id=new_school.id,
        must_change_password=True,
    )
    db.add(admin_user)

    # Audit lands in the NEW school's log — this is the cross-tenant
    # case that Phase 3 asks for. The SUPER_ADMIN's own tenant does
    # not get a duplicate row; the new tenant is the source of truth.
    write_audit_log(
        db, actor=current_user, action="SCHOOL_CREATED",
        details=(
            f"School '{body.name}' (slug={body.slug}) provisioned by "
            f"SUPER_ADMIN. Initial admin: {body.admin_email}."
        ),
        target_school_id=new_school.id,
    )
    db.commit()

    return {
        "id": new_school.id,
        "slug": new_school.slug,
        "name": new_school.name,
        "organization_id": new_school.organization_id,
        "bootstrap_admin": {
            "email": body.admin_email,
            # Returned once — never persisted in plaintext, never emitted
            # in logs. The super_admin is responsible for delivering it.
            "initial_password": bootstrap_pw,
        },
    }


@router.get("/schools")
def list_schools(
    db: Session = Depends(get_admin_db),
    current_user: User = Depends(require_super_admin),
):
    rows = db.query(School).order_by(School.id).all()
    return [
        {"id": s.id, "slug": s.slug, "name": s.name,
         "organization_id": s.organization_id, "status": s.status}
        for s in rows
    ]
