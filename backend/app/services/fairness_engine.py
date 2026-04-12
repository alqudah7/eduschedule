from typing import List, Any


class FairnessEngine:
    @staticmethod
    def duty_load(teacher: Any) -> float:
        count = len(teacher.duties) if hasattr(teacher, "duties") and teacher.duties else 0
        max_d = teacher.max_duties if teacher.max_duties else 16
        return (count / max_d) * 100

    @classmethod
    def rank_substitutes(
        cls,
        teachers: List[Any],
        required_qual: str,
        exclude_id: str,
    ) -> List[dict]:
        eligible = [
            t for t in teachers
            if t.id != exclude_id
            and t.status == "ACTIVE"
            and required_qual in (t.qualifications or [])
        ]
        ranked = sorted(eligible, key=lambda t: cls.duty_load(t))
        return [
            {
                "teacher": t,
                "load_pct": round(cls.duty_load(t), 1),
                "score": round(100 - cls.duty_load(t), 1),
            }
            for t in ranked[:5]
        ]
