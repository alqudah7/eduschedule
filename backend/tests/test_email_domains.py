"""Placeholder / reserved email-domain rejection."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
os.environ.setdefault("JWT_SECRET", "test")

import pytest

from app.utils.email_domains import (
    PlaceholderDomainError, assert_domain_usable_for_admin,
)


# ── real work-email domains (should NOT raise) ─────────────────────────────


@pytest.mark.parametrize("email", [
    "baraa@alhekma.com",
    "principal@sunrise-academy.edu",
    "admin@upper-case-Domain.CO.UK",
    "someone@school.education",
    "j.smith+admin@school.edu.sa",
])
def test_real_domains_are_accepted(email):
    assert_domain_usable_for_admin(email)  # no exception → pass


# ── RFC 6761 / 6762 reserved TLDs ─────────────────────────────────────────


@pytest.mark.parametrize("email", [
    "admin@school.test",
    "root@internal.test",
    "user@some.example",
    "person@some.invalid",
    "u@localhost",
    "u@printer.local",  # RFC 6762 mDNS
])
def test_reserved_tld_rejected(email):
    with pytest.raises(PlaceholderDomainError):
        assert_domain_usable_for_admin(email)


# ── RFC 2606 reserved second-level ─────────────────────────────────────────


@pytest.mark.parametrize("email", [
    "admin@example.com",
    "admin@Example.COM",       # case-insensitive
    "root@corp.example.com",   # subdomain of a reserved SLD
    "admin@example.net",
    "admin@example.org",
])
def test_example_domains_rejected(email):
    with pytest.raises(PlaceholderDomainError):
        assert_domain_usable_for_admin(email)


# ── Project placeholder (the exact motivating case) ────────────────────────


@pytest.mark.parametrize("email", [
    "admin@eduschedule.com",
    "sarah@eduschedule.com",
    "someone@subteam.eduschedule.com",
    "root@eduschedule.dev",
])
def test_project_placeholder_rejected(email):
    """The exact motivating case — reject the seed domain so a
    provisioning run can't recreate the anti-pattern we just cleaned
    out. eduschedule.local is separately covered by the TLD-reserved
    test above (.local trips first, which is also correct)."""
    with pytest.raises(PlaceholderDomainError) as exc:
        assert_domain_usable_for_admin(email)
    # Error message must name the seed domain so an operator reading
    # the API response knows what to change, not just "invalid".
    assert "eduschedule" in exc.value.reason.lower() or \
           "placeholder" in exc.value.reason.lower()


# ── syntactic guard ───────────────────────────────────────────────────────


def test_missing_at_rejected():
    with pytest.raises(PlaceholderDomainError):
        assert_domain_usable_for_admin("no-at-sign")


def test_empty_domain_rejected():
    with pytest.raises(PlaceholderDomainError):
        assert_domain_usable_for_admin("admin@")


def test_trailing_dot_stripped_before_matching():
    """A trailing dot on the domain (technically FQDN root) should not
    let 'example.com.' sneak past the 'example.com' block."""
    with pytest.raises(PlaceholderDomainError):
        assert_domain_usable_for_admin("admin@example.com.")
