from typing import List, Any, Optional
from app.services.free_period_engine import FreePeriodEngine

# Level adjacency: each level's ordered neighbours (closest first)
LEVEL_CHAIN: dict[str, list[str]] = {
    "ELEMENTARY": ["ELEMENTARY", "MIDDLE", "HIGH"],
    "MIDDLE":     ["MIDDLE", "ELEMENTARY", "HIGH"],
    "HIGH":       ["HIGH", "MIDDLE", "ELEMENTARY"],
    "ALL":        ["ALL", "ELEMENTARY", "MIDDLE", "HIGH"],
}


def _level_tier(teacher_level: str, required_level: str) -> int:
    """Lower tier number = better match."""
    if required_level == "ALL" or teacher_level == "ALL":
        return 1
    chain = LEVEL_CHAIN.get(required_level, [])
    try:
        return chain.index(teacher_level)
    except ValueError:
        return 99


class SubstitutionEngine:
    """
    Ranks substitute teachers using a cascading strategy:

    Tier 0 — same subject + same level + free at required time
    Tier 1 — same subject + adjacent level + free
    Tier 2 — same subject + any level + free
    Tier 3 — any teacher free at required time (workload-sorted fallback)
    """

    @staticmethod
    def _duty_load(teacher: Any) -> float:
        count = len(teacher.duties) if teacher.duties else 0
        max_d = teacher.max_duties or 16
        return (count / max_d) * 100

    @classmethod
    def rank_substitutes(
        cls,
        teachers: List[Any],
        absent_teacher: Any,
        day: str,
        start_time: str,
        end_time: str,
        max_results: int = 8,
    ) -> List[dict]:
        absent_id = absent_teacher.id
        absent_level = getattr(absent_teacher, "school_level", "ALL") or "ALL"
        absent_subjects = set(s.lower() for s in (absent_teacher.subjects or []))

        candidates = []
        for t in teachers:
            if t.id == absent_id or t.status != "ACTIVE":
                continue
            if not FreePeriodEngine.is_free(t, day, start_time, end_time):
                continue

            teacher_level = getattr(t, "school_level", "ALL") or "ALL"
            teacher_subjects = set(s.lower() for s in (t.subjects or []))
            subject_match = bool(absent_subjects & teacher_subjects)
            level_tier = _level_tier(teacher_level, absent_level)
            load = cls._duty_load(t)

            # Assign suggestion tier (0=best)
            if subject_match and level_tier == 0:
                suggestion_tier = 0
            elif subject_match and level_tier == 1:
                suggestion_tier = 1
            elif subject_match:
                suggestion_tier = 2
            else:
                suggestion_tier = 3

            candidates.append({
                "teacher": t,
                "load_pct": round(load, 1),
                "score": round(100 - load, 1),
                "tier": suggestion_tier,
                "tier_label": _tier_label(suggestion_tier),
                "subject_match": subject_match,
                "level_match": teacher_level == absent_level or teacher_level == "ALL",
            })

        # Sort: tier first, then workload ascending (least loaded = preferred)
        candidates.sort(key=lambda c: (c["tier"], c["load_pct"]))
        return candidates[:max_results]


def _tier_label(tier: int) -> str:
    labels = {
        0: "Same subject & level",
        1: "Same subject, adjacent level",
        2: "Same subject",
        3: "Available (any subject)",
    }
    return labels.get(tier, "Available")
