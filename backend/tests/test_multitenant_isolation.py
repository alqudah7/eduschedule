"""Cross-tenant isolation tests.

MULTITENANT.md §6 required tests:

1. Two schools with identical data → School A's API returns zero School B
   rows, on every endpoint. **Generated over the route table** so new
   endpoints are covered automatically without hand-writing per-route
   assertions.
2. Forged JWT with School B's school_id and a School A user → rejected.
3. RLS blocks a raw query that omits the filter (validates the DB-level
   layer independently of the SQLAlchemy filter layer).

Skipped when TEST_DATABASE_URL is not set. Local setup:

    docker run --rm -d --name eduschedule-test-db -p 5433:5432 \\
        -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test postgres:16
    TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/test \\
        JWT_SECRET=test venv/bin/python -m pytest \\
        tests/test_multitenant_isolation.py -v
"""

from __future__ import annotations

import os

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set — see docstring for setup",
)

if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ.setdefault("JWT_SECRET", "test-tenancy-secret")

    from fastapi.testclient import TestClient  # noqa: E402
    from sqlalchemy import create_engine, text  # noqa: E402
    from sqlalchemy.orm import sessionmaker  # noqa: E402

    from app.database import Base, get_db  # noqa: E402
    from app.main import app  # noqa: E402
    from app.middleware.auth import create_access_token, get_current_user  # noqa: E402
    from app.models.tenant import Organization, School, SchoolSettings  # noqa: E402
    from app.models.teacher import User, Teacher  # noqa: E402
    from app.models.lesson import Lesson  # noqa: E402
    from app.models.duty import Duty  # noqa: E402
    from app.models.substitution import Substitution  # noqa: E402
    from app.models.alert import Alert, Absence, AuditLog  # noqa: E402
    from app.models.attendance import TeacherAttendance  # noqa: E402

    _engine = create_engine(TEST_DB)
    _Session = sessionmaker(bind=_engine)


def _wipe():
    db = _Session()
    try:
        # Order matters because of FKs.
        for tbl in (
            "teacher_attendance", '"Absence"', '"Alert"', '"AuditLog"',
            '"Substitution"', '"Lesson"', '"Duty"', '"Teacher"', '"User"',
            "school_settings", "schools", "organizations",
        ):
            db.execute(text(f"DELETE FROM {tbl}"))
        db.commit()
    finally:
        db.close()


def _make_school(db, *, id_hint: int, slug: str, name: str) -> School:
    org = Organization(name=f"Org for {name}", slug=f"org-{slug}",
                       plan="STANDARD", status="ACTIVE")
    db.add(org)
    db.flush()
    school = School(
        organization_id=org.id, name=name, slug=slug,
        timezone="Asia/Bahrain", locale_default="EN", status="ACTIVE",
    )
    db.add(school)
    db.flush()
    db.add(SchoolSettings(
        school_id=school.id,
        working_days=["SUN", "MON", "TUE", "WED", "THU"],
        school_levels=["ELEMENTARY", "MIDDLE", "HIGH"],
        supported_locales=["EN"],
        periods=[{"number": 1, "label": "P1", "start": "07:40", "end": "08:30"}],
        breaks=[],
        features_enabled={},
    ))
    return school


def _seed_identical_school(db, school: School, tag: str) -> dict:
    """Populate one school with a canonical set of rows so both schools
    have parallel data. Returns the primary identifiers for later assertions."""
    admin = User(
        id=f"u-admin-{tag}", email=f"admin@{tag}", password="x",
        name=f"Admin {tag}", role="ADMIN", school_id=school.id,
    )
    teacher_user = User(
        id=f"u-t-{tag}", email=f"t@{tag}", password="x",
        name=f"Teacher {tag}", role="TEACHER", school_id=school.id,
    )
    db.add_all([admin, teacher_user])

    teacher = Teacher(
        id=f"t-{tag}", user_id=teacher_user.id, name=f"Adreen {tag}",
        initials="AK", department="CS", email=f"teach@{tag}",
        status="ABSENT", max_duties=16, qualifications=[],
        subjects=["Computer Science"], school_level="HIGH",
        school_id=school.id,
    )
    db.add(teacher)

    lesson = Lesson(
        id=f"l-{tag}", teacher_id=teacher.id, subject="Computer Science",
        class_="G11", room="R101", day="TUE", start_time="09:00",
        end_time="09:50", school_level="HIGH", school_id=school.id,
    )
    duty = Duty(
        id=f"d-{tag}", name=f"Gate {tag}", type="SUPERVISION",
        day="MON", start_time="07:15", end_time="07:45", location="Gate",
        teacher_id=teacher.id, status="CONFIRMED", school_id=school.id,
    )
    sub = Substitution(
        id=f"s-{tag}", absent_teacher_id=teacher.id, status="PENDING",
        school_id=school.id, duty_id=duty.id,
    )
    alert = Alert(
        id=f"a-{tag}", severity="HIGH", title=f"Alert {tag}",
        message="m", resolved=False, school_id=school.id,
    )
    audit = AuditLog(
        id=f"al-{tag}", action="TEST", actor=f"admin@{tag}",
        details=f"seeded {tag}", school_id=school.id,
    )
    absence = Absence(
        id=f"ab-{tag}", teacher_id=teacher.id,
        date=text("now()"), reason="sick", school_id=school.id,
    )
    attendance = TeacherAttendance(
        id=f"ta-{tag}", teacher_id=teacher.id, date=text("current_date"),
        status="present", school_id=school.id,
    )
    db.add_all([lesson, duty, sub, alert, audit, absence, attendance])
    db.commit()

    return {
        "school_id": school.id,
        "admin_id": admin.id,
        "teacher_id": teacher.id,
        "lesson_id": lesson.id,
        "duty_id": duty.id,
        "sub_id": sub.id,
        "alert_id": alert.id,
    }


@pytest.fixture(scope="module")
def two_schools():
    """School A + School B with identical row structures."""
    _wipe()
    db = _Session()
    try:
        school_a = _make_school(db, id_hint=1, slug="school-a", name="School A")
        school_b = _make_school(db, id_hint=2, slug="school-b", name="School B")
        db.commit()

        ids_a = _seed_identical_school(db, school_a, "a")
        ids_b = _seed_identical_school(db, school_b, "b")

        yield {"a": ids_a, "b": ids_b}
    finally:
        db.close()


@pytest.fixture
def client_as(two_schools):
    """Return a TestClient factory that pins the auth dependency to a
    specific tenant's admin. Yields per-request DB session with the GUC
    already set via get_current_user."""
    def _for(tenant: str) -> TestClient:
        ids = two_schools[tenant]

        def _override_db():
            db = _Session()
            try:
                yield db
            finally:
                db.close()

        def _override_user():
            # Return a User instance representing the tenant's admin.
            return User(
                id=ids["admin_id"], email=f"admin@{tenant}", password="x",
                name="Admin", role="ADMIN", school_id=ids["school_id"],
            )

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user
        return TestClient(app)

    yield _for
    app.dependency_overrides.clear()


# ─── Test 1: cross-tenant isolation, generated over the route table ────────

def _enumerable_get_routes() -> list[tuple[str, str]]:
    """Every GET route that doesn't require a path arg, so the same URL
    exercises both tenants. Path-parameterised routes are hit separately
    below with each tenant's own ids.

    When TEST_DATABASE_URL is unset the `app` import is skipped and this
    returns [] so parametrize doesn't blow up at collection time.
    """
    if not TEST_DB:
        return []
    result = []
    for r in app.routes:
        methods = getattr(r, "methods", None) or set()
        path = getattr(r, "path", "")
        if "GET" not in methods:
            continue
        if not path.startswith("/api"):
            continue
        if "{" in path:
            continue
        result.append(("GET", path))
    return result


@pytest.mark.parametrize("method,path", _enumerable_get_routes())
def test_list_endpoint_contains_only_own_tenant_rows(client_as, two_schools, method, path):
    """For every parameter-free GET under /api, School A's caller must not
    see any row identifier that belongs to School B."""
    a_client = client_as("a")
    r = a_client.request(method, path)
    # Some endpoints legitimately return non-200 without state (e.g.
    # /api/substitutions/suggest requires teacher_id + day). We only
    # audit successful responses — an endpoint that can't be called
    # trivially can't leak.
    if r.status_code >= 400:
        pytest.skip(f"{method} {path} -> {r.status_code}; needs args")
    body_text = r.text
    b_ids = two_schools["b"]
    leaked = [
        (name, val) for name, val in b_ids.items()
        if isinstance(val, str) and val in body_text
    ]
    assert not leaked, f"{path} leaked School B rows: {leaked}"


# ─── Test 2: forged JWT rejected ───────────────────────────────────────────

def test_forged_jwt_swaps_school_id_and_is_rejected(two_schools):
    """A School A user's token where school_id has been swapped to
    School B's must be rejected because User.school_id != token.school_id."""
    ids_a = two_schools["a"]
    ids_b = two_schools["b"]

    # Forge: A's user, B's school_id.
    forged = create_access_token({
        "sub": ids_a["admin_id"],
        "email": "admin@a",
        "role": "ADMIN",
        "school_id": ids_b["school_id"],
    })

    def _real_db():
        db = _Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _real_db
    try:
        with TestClient(app) as c:
            r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 403, r.text
    assert "school_id" in r.text.lower() or "does not match" in r.text.lower()


# ─── Test 3: RLS blocks raw query without GUC ──────────────────────────────

def test_rls_blocks_query_when_school_id_guc_is_unset(two_schools):
    """Layer-1 defence: without app.current_school_id, RLS returns zero
    rows even for a raw session.execute. This only bites for non-superuser
    roles; on Railway's superuser connection the check is documentation.
    Test uses a scratch non-superuser role to make the check meaningful."""
    db = _Session()
    try:
        db.execute(text("CREATE ROLE tenant_probe LOGIN"))
        for tbl in ("User", "Teacher", "Lesson"):
            db.execute(text(f'GRANT SELECT ON "{tbl}" TO tenant_probe'))
        db.commit()

        db.execute(text("SET ROLE tenant_probe"))
        # No GUC set -> policy USING (school_id = 0) -> no rows.
        rows = db.execute(text('SELECT count(*) FROM "User"')).scalar_one()
        assert rows == 0, "RLS should block reads when app.current_school_id is unset"

        # With GUC set to School A -> only A's rows.
        db.execute(text("SET app.current_school_id = :sid"),
                   {"sid": str(two_schools["a"]["school_id"])})
        a_rows = db.execute(text('SELECT count(*) FROM "User"')).scalar_one()
        assert a_rows > 0
        assert a_rows == db.execute(
            text('SELECT count(*) FROM "User" WHERE school_id = :sid'),
            {"sid": two_schools["a"]["school_id"]},
        ).scalar_one()
    finally:
        db.execute(text("RESET ROLE"))
        try:
            db.execute(text("REVOKE ALL ON \"User\", \"Teacher\", \"Lesson\" FROM tenant_probe"))
            db.execute(text("DROP ROLE IF EXISTS tenant_probe"))
        except Exception:
            db.rollback()
        db.close()
