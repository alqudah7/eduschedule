"""Single source of truth for weekday representations.

The database stores days as 3-letter uppercase codes (SUN, MON, TUE, WED, THU).
API callers and CSV imports sometimes pass long form ("Tuesday") or mixed case
("tue"). All internal comparisons must go through ``normalize_day`` so a
mismatch cannot silently cause a filter to return nothing.
"""

from __future__ import annotations

from typing import Final

CANONICAL_DAYS: Final[tuple[str, ...]] = ("SUN", "MON", "TUE", "WED", "THU")

_ALIASES: Final[dict[str, str]] = {
    "SUNDAY": "SUN", "MONDAY": "MON", "TUESDAY": "TUE",
    "WEDNESDAY": "WED", "THURSDAY": "THU",
    "FRIDAY": "FRI", "SATURDAY": "SAT",
    "SUN": "SUN", "MON": "MON", "TUE": "TUE",
    "WED": "WED", "THU": "THU", "FRI": "FRI", "SAT": "SAT",
}


def normalize_day(day: str | None) -> str:
    """Return the canonical 3-letter uppercase day code.

    Unknown or empty inputs pass through as uppercased/empty so a bad value
    reaches the database as a string that simply matches nothing, rather than
    raising and breaking the request. Use ``is_school_day`` to validate.
    """
    if not day:
        return ""
    return _ALIASES.get(day.strip().upper(), day.strip().upper())


def is_school_day(day: str | None) -> bool:
    """True if the normalised day falls within the SUN–THU school week."""
    return normalize_day(day) in CANONICAL_DAYS
