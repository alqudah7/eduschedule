"""Whole-day substitution planner.

Given an absent teacher and a day, produces a ranked plan covering every
period at once. Ranking rules match the product spec:

    Tier 1 — same subject AND same school level
    Tier 2 — same subject (any level)
    Tier 3 — same school level (any subject)
    Tier 4 — any free teacher

Within a tier, prefer the teacher with the fewest substitutions already
assigned that day (existing + batch-so-far). If a candidate is already
covering (or the current top pick for) an adjacent period for this same
absent teacher, apply a continuity bonus of 1 tier. That bonus is enough
to promote a same-tier match ahead of the load-sorted default and to
promote a Tier 4 candidate to Tier 3, but never overrides subject match.

Constraints enforced at suggestion time (also re-checked at commit):
- Candidate is not the absent teacher.
- Candidate has no lesson at the target time.
- Candidate has no duty at the target time.
- Candidate has no existing substitution overlapping the target time.
- Within the batch, a candidate never appears as the top pick for two
  overlapping periods.

Lessons on the day that already have a substitution request are surfaced
as-is with the existing assignment; no new suggestions are computed.
Lessons with zero candidates are returned flagged `uncovered=True` so
the admin sees them (not silently omitted).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.utils.days import normalize_day


LEVEL_MATCH_ANY = "ALL"

TIER_SAME_SUBJECT_SAME_LEVEL = 1
TIER_SAME_SUBJECT = 2
TIER_SAME_LEVEL = 3
TIER_ANY_FREE = 4

TIER_LABELS: dict[int, str] = {
    TIER_SAME_SUBJECT_SAME_LEVEL: "Same subject & level",
    TIER_SAME_SUBJECT: "Same subject",
    TIER_SAME_LEVEL: "Same level",
    TIER_ANY_FREE: "Available",
}

CONTINUITY_BONUS_TIERS = 1  # promote by this many tiers when adjacent-covering


@dataclass(frozen=True)
class TimeWindow:
    day: str
    start: str
    end: str

    def overlaps(self, other_start: str, other_end: str, other_day: str) -> bool:
        if self.day != normalize_day(other_day):
            return False
        return _to_minutes(self.start) < _to_minutes(other_end) and \
               _to_minutes(other_start) < _to_minutes(self.end)


def _to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _teacher_subjects(t: Any) -> set[str]:
    """Return lower-cased subject set; fall back to lessons-taught set."""
    declared = {s.lower() for s in (t.subjects or [])}
    if declared:
        return declared
    return {l.subject.lower() for l in (t.lessons or [])}


def _teacher_effective_level(t: Any) -> str:
    """A teacher tagged 'ALL' who only teaches one level effectively is that level."""
    level = getattr(t, "school_level", LEVEL_MATCH_ANY) or LEVEL_MATCH_ANY
    if level == LEVEL_MATCH_ANY and t.lessons:
        distinct = {l.school_level for l in t.lessons if l.school_level and l.school_level != LEVEL_MATCH_ANY}
        if len(distinct) == 1:
            return distinct.pop()
    return level


def _levels_match(teacher_level: str, lesson_level: str) -> bool:
    return teacher_level == lesson_level or \
           teacher_level == LEVEL_MATCH_ANY or lesson_level == LEVEL_MATCH_ANY


def _tier_for(teacher: Any, lesson: Any) -> tuple[int, bool, bool]:
    """Return (tier, subject_match, level_match) for a candidate against a lesson."""
    lesson_level = lesson.school_level or LEVEL_MATCH_ANY
    subject_match = lesson.subject.lower() in _teacher_subjects(teacher)
    level_match = _levels_match(_teacher_effective_level(teacher), lesson_level)

    if subject_match and level_match:
        return TIER_SAME_SUBJECT_SAME_LEVEL, subject_match, level_match
    if subject_match:
        return TIER_SAME_SUBJECT, subject_match, level_match
    if level_match:
        return TIER_SAME_LEVEL, subject_match, level_match
    return TIER_ANY_FREE, subject_match, level_match


class Availability:
    """Per-teacher busy intervals for a given day.

    Sources merged:
    - Their own scheduled lessons
    - Their assigned duties (excluding cancelled)
    - Substitutions where they are the assigned substitute (PENDING or ACCEPTED)

    Held once per planning request so per-lesson candidate checks are O(k)
    over a small list rather than DB round-trips.
    """

    def __init__(self, day: str):
        self.day = normalize_day(day)
        self._busy: dict[str, list[tuple[str, str]]] = {}
        self._sub_load: dict[str, int] = {}

    def add_lessons(self, teacher: Any) -> None:
        for l in teacher.lessons or []:
            if normalize_day(l.day) == self.day:
                self._busy.setdefault(teacher.id, []).append((l.start_time, l.end_time))

    def add_duties(self, teacher: Any) -> None:
        for d in teacher.duties or []:
            if d.status == "CANCELLED":
                continue
            if normalize_day(d.day) == self.day:
                self._busy.setdefault(teacher.id, []).append((d.start_time, d.end_time))

    def add_existing_substitution(
        self, substitute_id: str, slot_day: str, slot_start: str, slot_end: str,
    ) -> None:
        if normalize_day(slot_day) != self.day:
            return
        self._busy.setdefault(substitute_id, []).append((slot_start, slot_end))
        self._sub_load[substitute_id] = self._sub_load.get(substitute_id, 0) + 1

    def is_free(self, teacher_id: str, start: str, end: str) -> bool:
        for bs, be in self._busy.get(teacher_id, []):
            if _to_minutes(start) < _to_minutes(be) and _to_minutes(bs) < _to_minutes(end):
                return False
        return True

    def sub_load(self, teacher_id: str) -> int:
        return self._sub_load.get(teacher_id, 0)

    def reserve(self, teacher_id: str, start: str, end: str) -> None:
        """Add a batch-level reservation so the next lesson doesn't double-book."""
        self._busy.setdefault(teacher_id, []).append((start, end))
        self._sub_load[teacher_id] = self._sub_load.get(teacher_id, 0) + 1


def _serialise_teacher(t: Any) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "initials": t.initials,
        "department": t.department,
        "school_level": _teacher_effective_level(t),
        "subjects": list(t.subjects or []),
    }


def _serialise_lesson(l: Any) -> dict:
    return {
        "id": l.id,
        "subject": l.subject,
        "class": l.class_,
        "room": l.room,
        "day": l.day,
        "start_time": l.start_time,
        "end_time": l.end_time,
        "school_level": l.school_level,
    }


class DayPlanner:
    """Build a whole-day substitution plan.

    Usage:

        planner = DayPlanner(
            absent_teacher=teacher,
            day="TUE",
            candidate_pool=active_teachers,
            availability=Availability(day="TUE"),
        )
        for t in active_teachers:
            planner.availability.add_lessons(t)
            planner.availability.add_duties(t)
        for existing_sub in day_subs_with_substitute:
            planner.availability.add_existing_substitution(...)

        plan = planner.build(lessons_sorted_by_start, existing_subs_by_lesson_id)
    """

    def __init__(
        self,
        absent_teacher: Any,
        day: str,
        candidate_pool: Iterable[Any],
        availability: Availability,
    ):
        self.absent_teacher = absent_teacher
        self.day = normalize_day(day)
        self.candidate_pool = [t for t in candidate_pool if t.id != absent_teacher.id and t.status == "ACTIVE"]
        self.availability = availability

    def _candidates_for(
        self,
        lesson: Any,
        previous_top_id: str | None,
    ) -> list[dict]:
        """Rank all eligible candidates for a single lesson."""
        results = []
        for t in self.candidate_pool:
            if not self.availability.is_free(t.id, lesson.start_time, lesson.end_time):
                continue

            tier, subject_match, level_match = _tier_for(t, lesson)
            continuity_bonus = CONTINUITY_BONUS_TIERS if previous_top_id == t.id else 0
            effective_tier = max(1, tier - continuity_bonus)

            load = self.availability.sub_load(t.id)
            results.append({
                "teacher": _serialise_teacher(t),
                "tier": tier,
                "tier_label": TIER_LABELS[tier],
                "effective_tier": effective_tier,
                "subject_match": subject_match,
                "level_match": level_match,
                "current_load": load,
                "continuity_bonus": continuity_bonus > 0,
            })
        # Primary key: effective_tier ascending. Secondary: load ascending.
        # Tertiary: raw tier (so within same effective_tier, unbonused stronger tier wins).
        # Quaternary: name (deterministic tie-break).
        results.sort(key=lambda c: (
            c["effective_tier"],
            c["current_load"],
            c["tier"],
            c["teacher"]["name"],
        ))
        return results

    def build(
        self,
        lessons: list[Any],
        existing_subs_by_lesson_id: dict[str, Any],
        max_suggestions_per_lesson: int = 4,
    ) -> dict:
        """Return the whole-day plan.

        Args:
            lessons: absent teacher's lessons that day, sorted by start_time
            existing_subs_by_lesson_id: any Substitution rows already keyed to
                these lessons (rendered as-is; no new suggestions generated)
        """
        plan: list[dict] = []
        previous_top_id: str | None = None
        uncovered = 0

        for idx, lesson in enumerate(lessons):
            row: dict[str, Any] = {
                "period_index": idx + 1,
                "lesson": _serialise_lesson(lesson),
            }
            existing = existing_subs_by_lesson_id.get(lesson.id)
            if existing is not None:
                row["existing_substitution_id"] = existing.id
                row["existing_status"] = existing.status
                row["existing_substitute_id"] = existing.substitute_id
                row["suggestions"] = []
                row["uncovered"] = False
                # For continuity: if the existing sub has a substitute, that
                # substitute is the "adjacent covering" candidate for the next
                # period.
                previous_top_id = existing.substitute_id
                plan.append(row)
                continue

            candidates = self._candidates_for(lesson, previous_top_id)
            row["suggestions"] = candidates[:max_suggestions_per_lesson]
            row["uncovered"] = len(candidates) == 0

            if candidates:
                top_id = candidates[0]["teacher"]["id"]
                # Reserve the top pick so subsequent lessons don't double-book.
                self.availability.reserve(top_id, lesson.start_time, lesson.end_time)
                previous_top_id = top_id
            else:
                previous_top_id = None
                uncovered += 1

            plan.append(row)

        return {
            "teacher_id": self.absent_teacher.id,
            "teacher_name": self.absent_teacher.name,
            "day": self.day,
            "total_lessons": len(lessons),
            "uncovered_count": uncovered,
            "plan": plan,
        }
