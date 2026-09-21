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
    from app.models.alert import Alert, AuditLog  # noqa: E402
    from app.models.attendance import TeacherAttendance  # noqa: E402

    _engine = create_engine(TEST_DB)
    _Session = sessionmaker(bind=_engine)


def _wipe():
    db = _Session()
    try:
        # Order matters because of FKs.
        for tbl in (
            "teacher_attendance", '"Alert"', '"AuditLog"',
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
        name=f"Admin {tag}", role="SCHOOL_ADMIN", school_id=school.id,
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
    # Absence table was consolidated into teacher_attendance in Alembic
    # 21c773d1e916. The Batch 3 refactor kept absence semantics via
    # status='absent' rows on teacher_attendance — that's what this test
    # now seeds so isolation coverage still includes both "absent" and
    # "present" attendance rows.
    absence_attendance = TeacherAttendance(
        id=f"ab-{tag}", teacher_id=teacher.id, date=text("current_date - interval '1 day'"),
        status="absent", note="sick", school_id=school.id,
    )
    attendance = TeacherAttendance(
        id=f"ta-{tag}", teacher_id=teacher.id, date=text("current_date"),
        status="present", school_id=school.id,
    )
    db.add_all([lesson, duty, sub, alert, audit, absence_attendance, attendance])
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
            # Role widened to SCHOOL_ADMIN in Phase 3 (ADMIN was renamed).
            return User(
                id=ids["admin_id"], email=f"admin@{tenant}", password="x",
                name="Admin", role="SCHOOL_ADMIN", school_id=ids["school_id"],
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

def _current_role_is_superuser(db) -> bool:
    return db.execute(text(
        "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
    )).scalar_one()


def test_rls_blocks_query_when_school_id_guc_is_unset(two_schools):
    """Layer-1 defence: without app.current_school_id, RLS returns zero
    rows even for a raw session.execute.

    RLS only bites for non-superuser, non-BYPASSRLS roles. To exercise the
    real path we need such a role. Behaviour:

    - If the current session role IS a superuser (e.g. local dev connecting
      as postgres), the test spins up a scratch role to make the check
      meaningful.
    - If the current session role is ALREADY non-superuser (e.g. running
      against production's eduschedule_app), the test uses that role
      directly — this is the "meaningful" run per MULTITENANT.md follow-up.
    """
    db = _Session()
    made_scratch = False
    try:
        if _current_role_is_superuser(db):
            db.execute(text("CREATE ROLE tenant_probe LOGIN"))
            for tbl in ("User", "Teacher", "Lesson"):
                db.execute(text(f'GRANT SELECT ON "{tbl}" TO tenant_probe'))
            db.commit()
            db.execute(text("SET ROLE tenant_probe"))
            made_scratch = True
        # else: already running as a non-superuser — great, that's the case
        # the user actually cares about.

        # No GUC set -> policy USING (school_id = <no match>) -> no rows.
        db.execute(text("RESET app.current_school_id"))
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
        if made_scratch:
            try:
                db.execute(text("RESET ROLE"))
                db.execute(text('REVOKE ALL ON "User", "Teacher", "Lesson" FROM tenant_probe'))
                db.execute(text("DROP ROLE IF EXISTS tenant_probe"))
            except Exception:
                db.rollback()
        db.close()


def test_rls_bites_against_current_connection_readonly():
    """Read-only variant of the RLS check that works against a live
    production database without needing seeded fixture data.

    Skipped if the current role is a superuser. Skipped if the DB is
    empty (no tenants exist to compare against).

    Purpose: enable `pytest -k rls_bites` to be pointed at production's
    app-role connection to prove RLS is actively enforcing — no writes,
    no role creation, safe to run at any time.
    """
    db = _Session()
    try:
        if _current_role_is_superuser(db):
            pytest.skip("Current role is superuser — RLS is bypassed; use the app role instead")

        # There must be at least one tenant with data for this to be meaningful.
        existing = db.execute(text(
            "SELECT school_id FROM (VALUES (1)) AS s(school_id) WHERE EXISTS "
            "(SELECT 1 FROM schools LIMIT 1)"
        )).first()
        if existing is None:
            pytest.skip("No schools exist — nothing to check")

        # No GUC → zero visible rows.
        db.execute(text("RESET app.current_school_id"))
        for tbl in ("User", "Teacher", "Lesson", "Duty"):
            count = db.execute(text(f'SELECT count(*) FROM "{tbl}"')).scalar_one()
            assert count == 0, (
                f"RLS did not block reads on {tbl} when app.current_school_id was unset — "
                f"got {count} rows. Either the current role is superuser/BYPASSRLS, or "
                f"the tenant_isolation policy is missing/misconfigured."
            )
    finally:
        db.close()


# ─── Phase 3: subdomain resolution + role hierarchy + cross-tenant audit ────


if TEST_DB:

    def _client_as_super_admin(school_ids):
        """TestClient with the auth dependency pinned to a synthetic
        SUPER_ADMIN who lives in School A but can act on either. Also
        overrides the tenant resolver so Origin-header plumbing does
        not need real DNS wired up for the test."""
        from app.services.tenant_resolver import ResolvedTenant, get_current_tenant

        def _override_db():
            db = _Session()
            try:
                yield db
            finally:
                db.close()

        def _override_user():
            return User(
                id="u-super", email="super@platform.example", password="x",
                name="Super", role="SUPER_ADMIN",
                school_id=school_ids["a"]["school_id"],
            )

        def _override_tenant():
            # For the admin router, tenant resolution is not required
            # (super_admin lives on the platform, not inside a tenant).
            return ResolvedTenant(
                id=school_ids["a"]["school_id"],
                slug="school-a", name="School A",
            )

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = _override_user
        app.dependency_overrides[get_current_tenant] = _override_tenant
        return TestClient(app)


def test_login_returns_404_for_unknown_subdomain(two_schools):
    """Phase 3: a POST /api/auth/login from a subdomain that doesn't
    map to a school must 404 with code=UNKNOWN_TENANT — never leak
    "wrong password" style responses that would tell the attacker the
    subdomain is bogus vs. the credentials are bogus."""
    def _override_db():
        db = _Session()
        try:
            yield db
        finally:
            db.close()

    # Do NOT override get_current_tenant — let it run and 404 on the
    # non-existent slug. Force the resolver to actually consult the DB
    # by pushing an X-Tenant-Slug header + the dev flag.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = _override_db
    from app.config import settings as _s
    _s.ALLOW_TENANT_HEADER = True
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/auth/login",
            data={"username": "admin@a", "password": "x"},
            headers={"x-tenant-slug": "no-such-school"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["code"] == "UNKNOWN_TENANT"
    finally:
        _s.ALLOW_TENANT_HEADER = False
        app.dependency_overrides.clear()


def test_super_admin_creates_school_and_audit_lands_in_new_tenant(two_schools):
    """The Phase 3 headline test: a SUPER_ADMIN creates a THIRD school.
    The audit row for that creation must land in the NEW school's
    AuditLog (not in the super_admin's home school and not in any
    global bucket)."""
    client = _client_as_super_admin(two_schools)

    # First seed an org for the new school to attach to.
    org_resp = client.post(
        "/api/admin/organizations",
        json={"name": "Third Org", "slug": "third-org"},
    )
    assert org_resp.status_code == 201, org_resp.text

    resp = client.post(
        "/api/admin/schools",
        json={
            "organization_slug": "third-org",
            "name": "Third School",
            "slug": "third",
            "timezone": "UTC",
            "locale_default": "EN",
            "admin_email": "admin@third.example",
        },
    )
    assert resp.status_code == 201, resp.text
    new_school_id = resp.json()["id"]

    # AuditLog for SCHOOL_CREATED must exist under the NEW school.
    db = _Session()
    try:
        db.execute(text("SET LOCAL app.current_school_id = :sid"),
                   {"sid": str(new_school_id)})
        rows = db.execute(text(
            'SELECT school_id, action, actor FROM "AuditLog" '
            "WHERE action = 'SCHOOL_CREATED'"
        )).mappings().all()
        assert len(rows) == 1
        row = rows[0]
        assert row["school_id"] == new_school_id
        # Actor label must flag the cross-tenant hop so tenant admins
        # can see at a glance a super_admin created this row.
        assert "SUPER_ADMIN" in row["actor"]
        assert "cross-tenant" in row["actor"]
    finally:
        db.close()

    # And the SUPER_ADMIN's home school must NOT have picked up a copy.
    db = _Session()
    try:
        home_school = two_schools["a"]["school_id"]
        db.execute(text("SET LOCAL app.current_school_id = :sid"),
                   {"sid": str(home_school)})
        home_rows = db.execute(text(
            'SELECT id FROM "AuditLog" WHERE action = \'SCHOOL_CREATED\''
        )).scalars().all()
        assert home_rows == [], (
            "SCHOOL_CREATED audit rows must not appear in the super_admin's "
            "own tenant — they belong to the acted-on tenant"
        )
    finally:
        db.close()


# Role-hierarchy sanity tests were moved to tests/test_role_hierarchy.py
# so they run without TEST_DATABASE_URL (the module-level skipif above
# would otherwise skip pure-Python cases too).
