from typing import List, Any
from dataclasses import dataclass


@dataclass
class TimeWindow:
    day: str
    start_time: str
    end_time: str


class FreePeriodEngine:
    """Determines whether a teacher is free during a given time window."""

    @staticmethod
    def _to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    @classmethod
    def _overlaps(cls, a: TimeWindow, b_day: str, b_start: str, b_end: str) -> bool:
        if a.day != b_day:
            return False
        s1, e1 = cls._to_minutes(a.start_time), cls._to_minutes(a.end_time)
        s2, e2 = cls._to_minutes(b_start), cls._to_minutes(b_end)
        return s1 < e2 and s2 < e1

    @classmethod
    def is_free(
        cls,
        teacher: Any,
        day: str,
        start_time: str,
        end_time: str,
    ) -> bool:
        """Return True if teacher has no lesson or duty overlapping the window."""
        window = TimeWindow(day=day, start_time=start_time, end_time=end_time)

        for lesson in (teacher.lessons or []):
            if cls._overlaps(window, lesson.day, lesson.start_time, lesson.end_time):
                return False

        for duty in (teacher.duties or []):
            if duty.status == "CANCELLED":
                continue
            if cls._overlaps(window, duty.day, duty.start_time, duty.end_time):
                return False

        return True

    @classmethod
    def get_busy_slots(cls, teacher: Any) -> List[dict]:
        """Return all occupied slots for a teacher, sorted by day then time."""
        slots = []
        for lesson in (teacher.lessons or []):
            slots.append({
                "type": "lesson",
                "day": lesson.day,
                "start_time": lesson.start_time,
                "end_time": lesson.end_time,
                "label": lesson.subject,
                "school_level": getattr(lesson, "school_level", "ALL"),
            })
        for duty in (teacher.duties or []):
            if duty.status == "CANCELLED":
                continue
            slots.append({
                "type": "duty",
                "day": duty.day,
                "start_time": duty.start_time,
                "end_time": duty.end_time,
                "label": duty.name,
                "duty_category": getattr(duty, "duty_category", "SUPERVISION"),
            })
        return sorted(slots, key=lambda s: (s["day"], s["start_time"]))
