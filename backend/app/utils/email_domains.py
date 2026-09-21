"""Placeholder / reserved email-domain rejection.

Admin accounts get created with real work email addresses on the
school's own domain (baraa@alhekma.com, not admin@example.com). This
module refuses obviously-fake domains at the API boundary so a
provisioning call that would otherwise land a support ticket days later
fails immediately with a clear error code.

Layers of the blocklist:

  1. RFC 6761 reserved TLDs — .test / .example / .invalid / .localhost.
     These MUST NOT resolve on the public Internet, and cannot be
     legitimate admin addresses.

  2. RFC 6762 mDNS local — .local. Not intended for e-mail.

  3. RFC 2606 reserved second-level domains — example.com,
     example.net, example.org (and subdomains of them).

  4. Project-specific placeholders — eduschedule.com is the demo-seed
     domain and should never appear on a real tenant. Add here when
     new placeholders emerge.

Extensibility: the project-specific list is a module-level set so a
future setting could load additional entries from an env var without
rewriting the checks.
"""
from __future__ import annotations

# Case-insensitive suffix matches. "example.com" matches BOTH
# admin@example.com and admin@corp.example.com — the entire example
# reservation is off-limits.
_RESERVED_TLDS: frozenset[str] = frozenset({
    ".test", ".example", ".invalid", ".localhost", ".local",
})

_RESERVED_DOMAINS: frozenset[str] = frozenset({
    # RFC 2606 §3
    "example.com", "example.net", "example.org",
    # Project placeholders — the seed/demo domain and its variants.
    "eduschedule.com",
    "eduschedule.dev",
    "eduschedule.local",
})


class PlaceholderDomainError(ValueError):
    """Raised when an admin email uses a reserved / placeholder domain."""

    def __init__(self, domain: str, reason: str) -> None:
        super().__init__(f"{domain}: {reason}")
        self.domain = domain
        self.reason = reason


def _extract_domain(email: str) -> str:
    """Return the domain portion of an email, lowercased.

    Deliberately naive — full RFC 5321 validation belongs upstream (in
    pydantic's EmailStr / email-validator). This module only needs the
    domain, and it needs to be resilient to callers who forgot to pass
    through EmailStr.
    """
    if "@" not in email:
        raise PlaceholderDomainError(
            domain="",
            reason="Email is missing an '@' — not a valid address.",
        )
    domain = email.rsplit("@", 1)[1].strip().lower().rstrip(".")
    if not domain:
        raise PlaceholderDomainError(
            domain="",
            reason="Email has an empty domain.",
        )
    return domain


def assert_domain_usable_for_admin(email: str) -> None:
    """Raise PlaceholderDomainError if the email's domain is reserved.

    Called by the school-provisioning route so we cannot create a
    SCHOOL_ADMIN on a fake domain. Convention: every school's admin
    uses that school's own work email domain.
    """
    domain = _extract_domain(email)

    # RFC 6761 / 6762 reserved TLDs — check the last label.
    for reserved_tld in _RESERVED_TLDS:
        if domain == reserved_tld.lstrip(".") or domain.endswith(reserved_tld):
            raise PlaceholderDomainError(
                domain=domain,
                reason=(
                    f"Top-level domain {reserved_tld!s} is reserved and "
                    "cannot be used for real admin accounts (RFC 6761/6762)."
                ),
            )

    # Reserved second-level domains (RFC 2606) + project placeholders.
    for reserved in _RESERVED_DOMAINS:
        if domain == reserved or domain.endswith("." + reserved):
            raise PlaceholderDomainError(
                domain=domain,
                reason=(
                    f"Domain {reserved!r} is a reserved or placeholder "
                    "domain — admin accounts must use the school's real "
                    "work email domain (e.g. alhekma.com, not "
                    "eduschedule.com or example.com)."
                ),
            )
