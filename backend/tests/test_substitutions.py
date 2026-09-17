"""Contract tests for the Substitution → JSON serializer.

The Dashboard's SubRequestPanel branches on ``sub_type`` and reads either the
``lesson`` or the ``duty`` field. If this contract regresses, the panel
silently renders ``undefined–undefined``. These tests pin the shape.
"""

import os
from types import SimpleNamespace

# Router import triggers Settings() which requires these; set before import.
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("JWT_SECRET", "test")

from app.routers.substitutions import _sub_to_dict  # noqa: E402


def _teacher(name: str = "Test Teacher", initials: str = "TT") -> SimpleNamespace:
    return SimpleNamespace(id="t-fixture", name=name, initials=initials, department="Test Dept")


def _lesson() -> SimpleNamespace:
    return SimpleNamespace(
        id="lesson-1", subject="Computer Science", class_="10A", room="R101",
        day="TUE", start_time="09:00", end_time="09:50", school_level="HIGH",
    )


def _duty() -> SimpleNamespace:
    return SimpleNamespace(
        id="duty-1", name="Morning Gate", type="SUPERVISION", day="MON",
        start_time="07:15", end_time="07:45", location="Main Gate",
        status="CONFIRMED",
    )


class TestSubToDictLessonType:
    """Regression guard for the Dashboard fix (commit 27822f6 introduced
    the lesson variant; the original SubRequestPanel only read ``duty``)."""

    def test_sub_type_is_lesson(self) -> None:
        sub = SimpleNamespace(
            id="s1", duty_id=None, lesson_id="lesson-1",
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher("Adreen Khalil Haddad", "AK"),
            substitute=None, duty=None, lesson=_lesson(),
        )
        result = _sub_to_dict(sub)
        assert result["sub_type"] == "lesson"

    def test_lesson_id_populated_duty_id_null(self) -> None:
        sub = SimpleNamespace(
            id="s1", duty_id=None, lesson_id="lesson-1",
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher(), substitute=None, duty=None, lesson=_lesson(),
        )
        result = _sub_to_dict(sub)
        assert result["lesson_id"] == "lesson-1"
        assert result["duty_id"] is None

    def test_lesson_block_contains_time_day_room(self) -> None:
        # Dashboard SubRequestPanel reads exactly these keys.
        sub = SimpleNamespace(
            id="s1", duty_id=None, lesson_id="lesson-1",
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher(), substitute=None, duty=None, lesson=_lesson(),
        )
        result = _sub_to_dict(sub)
        assert result["lesson"]["start_time"] == "09:00"
        assert result["lesson"]["end_time"] == "09:50"
        assert result["lesson"]["day"] == "TUE"
        assert result["lesson"]["room"] == "R101"

    def test_duty_block_is_absent(self) -> None:
        # If both duty and lesson exist on a request, only one is populated.
        sub = SimpleNamespace(
            id="s1", duty_id=None, lesson_id="lesson-1",
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher(), substitute=None, duty=None, lesson=_lesson(),
        )
        result = _sub_to_dict(sub)
        assert "duty" not in result


class TestSubToDictDutyType:
    def test_sub_type_is_duty(self) -> None:
        sub = SimpleNamespace(
            id="s2", duty_id="duty-1", lesson_id=None,
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher(), substitute=None, duty=_duty(), lesson=None,
        )
        result = _sub_to_dict(sub)
        assert result["sub_type"] == "duty"

    def test_duty_block_contains_time_day_location(self) -> None:
        sub = SimpleNamespace(
            id="s2", duty_id="duty-1", lesson_id=None,
            absent_teacher_id="t1", substitute_id=None, status="PENDING",
            requested_at=None, resolved_at=None, notes=None,
            absent_teacher=_teacher(), substitute=None, duty=_duty(), lesson=None,
        )
        result = _sub_to_dict(sub)
        assert result["duty"]["start_time"] == "07:15"
        assert result["duty"]["end_time"] == "07:45"
        assert result["duty"]["day"] == "MON"
        assert result["duty"]["location"] == "Main Gate"
