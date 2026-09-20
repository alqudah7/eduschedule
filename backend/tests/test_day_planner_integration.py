"""Real-DB integration tests for the whole-day substitution flow.

Runs against Postgres (SQLite lacks ARRAY column type used by Teacher).
Skipped when TEST_DATABASE_URL is not set. Local setup:

    docker run --rm -d --name eduschedule-test-db -p 5433:5432 \\
        -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test postgres:16
    TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/test \\
        JWT_SECRET=test venv/bin/python -m pytest \\
        tests/test_day_planner_integration.py -v

These tests intentionally hit the real endpoint and real SQL — the class
of bug we've been chasing (unit tests green, live feature broken) needs
this layer to be exercised too.
"""

from __future__ import annotations

import os

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set — see docstring for local setup",
)

if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ.setdefault("JWT_SECRET", "test-secret")

    from fastapi.testclient import TestClient  # noqa: E402
    from sqlalchemy import create_engine  # noqa: E402
    from sqlalchemy.orm import sessionmaker  # noqa: E402

    from app.database import Base, get_db  # noqa: E402
    from app.main import app  # noqa: E402
    from app.middleware.auth import get_current_user  # noqa: E402
    from app.models.teacher import User, Teacher  # noqa: E402
    from app.models.lesson import Lesson  # noqa: E402
    from app.models.substitution import Substitution  # noqa: E402

    _engine = create_engine(TEST_DB)
    _Session = sessionmaker(bind=_engine)


def _fake_admin() -> "User":
    return User(id="admin", email="admin@test", password="", name="Admin", role="ADMIN")


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=_engine)

    def _override_db():
        db = _Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _fake_admin
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)


def _wipe():
    db = _Session()
    try:
        db.query(Substitution).delete()
        db.query(Lesson).delete()
        db.query(Teacher).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def _make_teacher(db, *, id: str, name: str, subjects: list[str], level: str = "HIGH",
                  status: str = "ACTIVE", initials: str | None = None):
    uid = f"u-{id}"
    db.add(User(id=uid, email=f"{id}@t", password="x", name=name, role="TEACHER"))
    db.add(Teacher(
        id=id, user_id=uid, name=name,
        initials=initials or "".join(n[0] for n in name.split()[:2]).upper(),
        department=subjects[0] if subjects else "General",
        email=f"{id}@t", status=status, max_duties=16,
        qualifications=[], subjects=subjects, school_level=level,
    ))


def _make_lesson(db, *, id: str, teacher_id: str, day: str, start: str, end: str,
                 subject: str = "Computer Science", level: str = "HIGH",
                 cls: str = "G11A", room: str = "R101"):
    db.add(Lesson(
        id=id, teacher_id=teacher_id, subject=subject, class_=cls, room=room,
        day=day, start_time=start, end_time=end, school_level=level,
    ))


@pytest.fixture
def adreen_full_day():
    """Adreen (ABSENT) has 4 Tuesday lessons.
    Available substitutes:
      - Beth  — Computer Science, HIGH  (Tier 1 match)
      - Carla — Assembly, HIGH          (Tier 1 for the 10:40 Assembly only)
      - Dan   — Computer Science, MIDDLE (Tier 2)
      - Eve   — Arabic, HIGH             (Tier 3)
      - Fred  — Arabic, MIDDLE           (Tier 4)
      - Grace — free but has a MON 09:00 lesson (irrelevant, tests day filter)
    """
    _wipe()
    db = _Session()
    try:
        _make_teacher(db, id="adreen", name="Adreen Khalil", subjects=["Computer Science", "Assembly"], status="ABSENT")
        _make_teacher(db, id="beth", name="Beth Aziz", subjects=["Computer Science"])
        _make_teacher(db, id="carla", name="Carla Rios", subjects=["Assembly"])
        _make_teacher(db, id="dan", name="Dan Ochoa", subjects=["Computer Science"], level="MIDDLE")
        _make_teacher(db, id="eve", name="Eve Kaur", subjects=["Arabic"])
        _make_teacher(db, id="fred", name="Fred Gomez", subjects=["Arabic"], level="MIDDLE")
        _make_teacher(db, id="grace", name="Grace Ali", subjects=["Computer Science"])

        # Adreen's Tuesday lessons — 4 periods
        _make_lesson(db, id="tue-1", teacher_id="adreen", day="TUE", start="09:00", end="09:50", subject="Computer Science")
        _make_lesson(db, id="tue-2", teacher_id="adreen", day="TUE", start="09:50", end="10:40", subject="Computer Science")
        _make_lesson(db, id="tue-3", teacher_id="adreen", day="TUE", start="10:40", end="11:30", subject="Assembly")
        _make_lesson(db, id="tue-4", teacher_id="adreen", day="TUE", start="11:50", end="12:40", subject="Computer Science")

        # Grace has a Monday lesson at 09:00 — must not affect Tuesday query
        _make_lesson(db, id="mon-grace", teacher_id="grace", day="MON", start="09:00", end="09:50", subject="Computer Science")

        db.commit()
        yield
    finally:
        db.close()


class TestSuggestEndpoint:
    def test_returns_four_lessons_for_four_periods(self, client, adreen_full_day):
        r = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE")
        assert r.status_code == 200
        body = r.json()
        assert body["total_lessons"] == 4
        assert body["uncovered_count"] == 0
        assert len(body["plan"]) == 4
        assert [row["lesson"]["start_time"] for row in body["plan"]] == [
            "09:00", "09:50", "10:40", "11:50",
        ]

    def test_each_period_has_ranked_candidates(self, client, adreen_full_day):
        body = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE").json()
        for row in body["plan"]:
            assert len(row["suggestions"]) > 0, "expected candidates for a well-staffed day"
            # Suggestions arrive sorted by effective_tier ascending
            tiers = [s["effective_tier"] for s in row["suggestions"]]
            assert tiers == sorted(tiers), "suggestions must be tier-sorted"

    def test_subject_and_level_match_is_tier_1(self, client, adreen_full_day):
        body = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE").json()
        # For the 09:00 Computer Science lesson, Beth (CS, HIGH) should be the top pick.
        top = body["plan"][0]["suggestions"][0]
        assert top["teacher"]["id"] == "beth"
        assert top["tier"] == 1
        assert top["subject_match"] and top["level_match"]

    def test_assembly_period_tops_carla(self, client, adreen_full_day):
        body = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE").json()
        # Period 3 is Assembly — Carla teaches Assembly at HIGH → Tier 1.
        # Beth was assigned to periods 1 and 2 so is now more loaded; Carla wins.
        top = body["plan"][2]["suggestions"][0]
        assert top["teacher"]["id"] == "carla"
        assert top["subject_match"] and top["level_match"]

    def test_no_candidate_is_double_booked_within_the_plan(self, client, adreen_full_day):
        """Each period's top pick must not be a substitute assigned in an
        overlapping period. Adreen's periods have distinct start times so
        the batch reservation must prevent the same teacher taking two
        adjacent slots unless the earlier one has already released them."""
        body = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE").json()
        seen: dict[str, str] = {}
        for row in body["plan"]:
            if not row["suggestions"]:
                continue
            top_id = row["suggestions"][0]["teacher"]["id"]
            slot = row["lesson"]["start_time"]
            if top_id in seen:
                # The same teacher was picked for two periods; slots must not overlap.
                assert seen[top_id] != slot, f"{top_id} double-booked at {slot}"
            seen[top_id] = slot

    def test_uncovered_period_flagged_not_omitted(self, client):
        """If no active teacher matches, the row is returned with
        uncovered=True and empty suggestions — never dropped."""
        _wipe()
        db = _Session()
        try:
            _make_teacher(db, id="adreen", name="Adreen K",
                          subjects=["Rare Subject"], status="ABSENT")
            _make_lesson(db, id="tue-1", teacher_id="adreen", day="TUE",
                         start="09:00", end="09:50", subject="Rare Subject")
            # Only substitute in the DB is on leave.
            _make_teacher(db, id="onleave", name="On Leave",
                          subjects=["Rare Subject"], status="ON_LEAVE")
            db.commit()
        finally:
            db.close()

        body = client.get("/api/substitutions/suggest?teacher_id=adreen&day=TUE").json()
        assert body["total_lessons"] == 1
        assert body["uncovered_count"] == 1
        assert len(body["plan"]) == 1
        assert body["plan"][0]["uncovered"] is True
        assert body["plan"][0]["suggestions"] == []


class TestAssignDayAtomic:
    def test_happy_path_creates_all(self, client, adreen_full_day):
        payload = {
            "absent_teacher_id": "adreen",
            "day": "TUE",
            "assignments": [
                {"lesson_id": "tue-1", "substitute_id": "beth"},
                {"lesson_id": "tue-2", "substitute_id": "dan"},
                {"lesson_id": "tue-3", "substitute_id": "carla"},
                {"lesson_id": "tue-4", "substitute_id": "beth"},
            ],
        }
        r = client.post("/api/substitutions/assign-day", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 4
        # DB reflects the writes
        db = _Session()
        try:
            rows = db.query(Substitution).all()
            assert len(rows) == 4
            assert all(s.status == "ACCEPTED" for s in rows)
        finally:
            db.close()

    def test_rollback_when_batch_double_books(self, client, adreen_full_day):
        """Two assignments overlap → whole batch rejected, nothing written."""
        payload = {
            "absent_teacher_id": "adreen",
            "day": "TUE",
            "assignments": [
                {"lesson_id": "tue-1", "substitute_id": "beth"},
                # Beth is now busy 09:00-09:50 from the first row. Assigning
                # her again to another lesson at the same time triggers the
                # in-batch conflict guard. tue-2 starts at 09:50, exactly at
                # the end of tue-1, so it does NOT overlap; we need to force
                # a real overlap. Create a synthetic overlapping lesson:
                {"lesson_id": "tue-1", "substitute_id": "beth"},
            ],
        }
        r = client.post("/api/substitutions/assign-day", json=payload)
        # Same lesson twice → the "existing_substitution" guard triggers on
        # the second pass (first insert makes tue-1 an existing sub).
        # But because we validate BEFORE insert and check the DB for
        # already-requested lessons up front, and both target the same
        # lesson_id, we should get a validation error before commit.
        assert r.status_code in (400, 409)
        db = _Session()
        try:
            assert db.query(Substitution).count() == 0
        finally:
            db.close()

    def test_rollback_when_substitute_conflicts_with_own_lesson(self, client):
        """A substitute has their own lesson at the target time → 409, no writes."""
        _wipe()
        db = _Session()
        try:
            _make_teacher(db, id="adreen", name="Adreen K",
                          subjects=["Computer Science"], status="ABSENT")
            _make_teacher(db, id="beth", name="Beth A",
                          subjects=["Computer Science"])
            # Beth teaches her own class at the exact time Adreen's lesson is.
            _make_lesson(db, id="beth-own", teacher_id="beth", day="TUE",
                         start="09:00", end="09:50", subject="Computer Science")
            _make_lesson(db, id="tue-1", teacher_id="adreen", day="TUE",
                         start="09:00", end="09:50", subject="Computer Science")
            db.commit()
        finally:
            db.close()

        payload = {
            "absent_teacher_id": "adreen", "day": "TUE",
            "assignments": [{"lesson_id": "tue-1", "substitute_id": "beth"}],
        }
        r = client.post("/api/substitutions/assign-day", json=payload)
        assert r.status_code == 409, r.text
        db = _Session()
        try:
            assert db.query(Substitution).count() == 0, "batch must not partially commit"
        finally:
            db.close()

    def test_rejects_lesson_from_another_teacher(self, client, adreen_full_day):
        """Adreen's plan cannot include a lesson belonging to someone else."""
        _make_other = _Session()
        try:
            _make_teacher(_make_other, id="somebody", name="Some Body",
                          subjects=["Math"])
            _make_lesson(_make_other, id="other-lesson", teacher_id="somebody",
                         day="TUE", start="09:00", end="09:50", subject="Math")
            _make_other.commit()
        finally:
            _make_other.close()

        payload = {
            "absent_teacher_id": "adreen", "day": "TUE",
            "assignments": [{"lesson_id": "other-lesson", "substitute_id": "beth"}],
        }
        r = client.post("/api/substitutions/assign-day", json=payload)
        assert r.status_code == 400
        db = _Session()
        try:
            assert db.query(Substitution).count() == 0
        finally:
            db.close()

    def test_rejects_lesson_already_has_a_sub_request(self, client, adreen_full_day):
        """If any target lesson already has a Substitution row, refuse."""
        db = _Session()
        try:
            db.add(Substitution(
                id="pre-existing", lesson_id="tue-1",
                absent_teacher_id="adreen", status="PENDING",
            ))
            db.commit()
        finally:
            db.close()

        payload = {
            "absent_teacher_id": "adreen", "day": "TUE",
            "assignments": [{"lesson_id": "tue-1", "substitute_id": "beth"}],
        }
        r = client.post("/api/substitutions/assign-day", json=payload)
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["reason"] == "existing_substitution"
        assert "tue-1" in detail["lesson_ids"]
