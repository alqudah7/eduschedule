"""Integration test for /api/substitutions/absent-lessons.

Hits the real FastAPI route with a real Postgres database and asserts on the
JSON body — no mocks in the layer where the actual bug lived. Auth is
overridden to a fake admin because setting up JWT signing is orthogonal to
what we're testing.

Requires TEST_DATABASE_URL to be set. Locally:

    docker run --rm -d --name eduschedule-test-db -p 5433:5432 \\
        -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test postgres:16
    TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/test \\
        JWT_SECRET=test venv/bin/python -m pytest \\
        tests/test_absent_lessons_integration.py -v

Skipped automatically when the env var is not set.

Why this class of test exists in addition to the unit tests:
- Unit tests (test_days, test_substitutions) proved the code was correct.
- The bug was actually "the code was never deployed" — that class of failure
  needs a post-deploy smoke test hitting the deployed API, which lives in
  ops/, not here.
- What THIS test catches: any regression that reintroduces day-format
  mismatch, breaks the WHERE clause, changes the response schema, or
  removes the route. All of those would have shown up here if this test
  had existed against the deployed API.
"""

import os

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set — see docstring for local setup",
)

# Point the app at the test DB *before* importing anything that touches
# app.config / app.database (module import binds the engine to DATABASE_URL).
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


@pytest.fixture
def adreen_with_tuesday_lessons():
    """Seed one absent teacher (Adreen), four Tuesday lessons, one Monday
    control lesson. Torn down after the test so tests don't cross-contaminate."""
    db = _Session()
    try:
        db.query(Lesson).delete()
        db.query(Teacher).delete()
        db.query(User).delete()
        db.commit()

        db.add(User(id="u-1", email="a@x", password="x", name="Adreen", role="TEACHER"))
        db.add(Teacher(
            id="t-adreen", user_id="u-1",
            name="Adreen Khalil Haddad", initials="AK", department="Computer Science",
            email="a@x", status="ABSENT", max_duties=16,
            qualifications=[], subjects=["Computer Science"],
            school_level="HIGH",
        ))
        tuesday_slots = [
            ("09:00", "09:50", "Computer Science"),
            ("09:50", "10:40", "Computer Science"),
            ("10:40", "11:30", "Assembly"),
            ("11:50", "12:40", "Computer Science"),
        ]
        for i, (start, end, subject) in enumerate(tuesday_slots):
            db.add(Lesson(
                id=f"lesson-tue-{i}", teacher_id="t-adreen",
                subject=subject, class_="G11", room="R101",
                day="TUE", start_time=start, end_time=end, school_level="HIGH",
            ))
        # Control row on a different day — must NOT appear in Tuesday results.
        db.add(Lesson(
            id="lesson-mon-control", teacher_id="t-adreen",
            subject="Should Not Appear", class_="G11", room="R101",
            day="MON", start_time="09:00", end_time="09:50", school_level="HIGH",
        ))
        db.commit()
        yield
    finally:
        db.close()


class TestAbsentLessonsEndpoint:
    def test_returns_all_four_tuesday_lessons(self, client, adreen_with_tuesday_lessons):
        r = client.get("/api/substitutions/absent-lessons?teacher_id=t-adreen&day=TUE")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 4
        assert all(lesson["day"] == "TUE" for lesson in body["lessons"])
        assert [lesson["start_time"] for lesson in body["lessons"]] == [
            "09:00", "09:50", "10:40", "11:50",
        ]

    def test_control_lesson_on_other_day_is_excluded(self, client, adreen_with_tuesday_lessons):
        r = client.get("/api/substitutions/absent-lessons?teacher_id=t-adreen&day=MON")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["lessons"][0]["subject"] == "Should Not Appear"

    def test_long_form_day_is_normalised(self, client, adreen_with_tuesday_lessons):
        """Regression guard: the original bug was the frontend sending
        'Tuesday' instead of 'TUE'. If normalize_day() ever regresses, this
        request will return 0 rows and this test will fail."""
        r = client.get("/api/substitutions/absent-lessons?teacher_id=t-adreen&day=Tuesday")
        assert r.status_code == 200
        assert r.json()["total"] == 4

    def test_unknown_teacher_returns_empty(self, client, adreen_with_tuesday_lessons):
        r = client.get("/api/substitutions/absent-lessons?teacher_id=nonexistent&day=TUE")
        assert r.status_code == 200
        assert r.json() == {"lessons": [], "total": 0}

    def test_response_shape_matches_frontend_contract(self, client, adreen_with_tuesday_lessons):
        """CoverClassesPanel reads: id, subject, class, room, day, start_time,
        end_time, school_level, substitution. Any missing key breaks the UI."""
        r = client.get("/api/substitutions/absent-lessons?teacher_id=t-adreen&day=TUE")
        first = r.json()["lessons"][0]
        for required in ("id", "subject", "class", "room", "day",
                         "start_time", "end_time", "school_level", "substitution"):
            assert required in first, f"missing key: {required}"
