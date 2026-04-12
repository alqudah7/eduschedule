from typing import List
from dataclasses import dataclass


@dataclass
class TimeSlot:
    day: str
    start_time: str
    end_time: str
    teacher_id: str
    label: str
    record_id: str
    record_type: str  # "duty" or "lesson"


class ConflictEngine:
    @staticmethod
    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    @classmethod
    def overlaps(cls, a: TimeSlot, b: TimeSlot) -> bool:
        if a.teacher_id != b.teacher_id:
            return False
        if a.day != b.day:
            return False
        if a.record_id == b.record_id and a.record_type == b.record_type:
            return False
        s1, e1 = cls.to_minutes(a.start_time), cls.to_minutes(a.end_time)
        s2, e2 = cls.to_minutes(b.start_time), cls.to_minutes(b.end_time)
        return s1 < e2 and s2 < e1

    @classmethod
    def find_conflicts(cls, target: TimeSlot, all_slots: List[TimeSlot]) -> List[TimeSlot]:
        return [s for s in all_slots if cls.overlaps(target, s)]
