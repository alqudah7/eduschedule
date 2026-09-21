import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.middleware.auth import require_current_password
from app.routers import auth, teachers, duties, schedule, substitutions, alerts, reports, attendance, admin

# Import all models so Base.metadata knows about them before create_all
import app.models.teacher  # noqa: F401
import app.models.duty  # noqa: F401
import app.models.lesson  # noqa: F401
import app.models.substitution  # noqa: F401
import app.models.alert  # noqa: F401
import app.models.attendance  # noqa: F401
import app.models.tenant  # noqa: F401  # organizations, schools, school_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="EduSchedule API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth router does NOT carry the must-change-password guard — login,
# logout, /me and /change-password have to work while the flag is set.
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Every other router mounts with require_current_password as a
# router-level dependency. A user whose must_change_password=TRUE gets
# a 428 Precondition Required from every endpoint below until they call
# /api/auth/change-password. This is enforcement — a client that hides
# the redirect UI is still blocked at the API layer.
_stale_pw_guard = [Depends(require_current_password)]

app.include_router(teachers.router, prefix="/api/teachers", tags=["teachers"], dependencies=_stale_pw_guard)
app.include_router(duties.router, prefix="/api/duties", tags=["duties"], dependencies=_stale_pw_guard)
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"], dependencies=_stale_pw_guard)
app.include_router(substitutions.router, prefix="/api/substitutions", tags=["substitutions"], dependencies=_stale_pw_guard)
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"], dependencies=_stale_pw_guard)
app.include_router(reports.router, prefix="/api/reports", tags=["reports"], dependencies=_stale_pw_guard)
app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"], dependencies=_stale_pw_guard)

# SUPER_ADMIN cross-tenant surface. Not gated on tenant resolution —
# a super_admin lives on the platform, not inside one school. Every
# route inside this router applies its own role guard.
app.include_router(admin.router, prefix="/api/admin", tags=["admin"], dependencies=_stale_pw_guard)


@app.on_event("startup")
def startup_probe() -> None:
    """Fail loudly if the DB is unreachable at boot.

    Schema management moved to Alembic (see backend/alembic/). This hook
    used to run ``Base.metadata.create_all`` + ad-hoc ALTER TABLE
    patches, but the app now connects as a non-superuser role that
    lacks DDL privileges — those calls would fail at runtime. The
    superuser-only ``MIGRATE_DATABASE_URL`` is used by Alembic (from
    ops, not at startup).

    All this hook does now is a SELECT 1 to make sure the connection
    string, credentials, and network path are valid before the API
    accepts traffic.
    """
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Startup DB probe failed — refusing to boot")
        raise


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/admin/seed")
def seed_database() -> dict:
    """Bootstrap an empty database with demo data.

    Non-destructive: if any User row exists, this is a no-op. There is no
    ``force`` parameter and no delete path — a wipe is not possible through
    this endpoint. Gated on environment: refuses to run in production.
    """
    if settings.ENV == "production":
        raise HTTPException(status_code=403, detail="Seeding disabled in production")

    import cuid as cuid_lib
    import secrets
    import sys
    from datetime import datetime, timezone

    from app.middleware.auth import hash_password
    from app.models.teacher import User, Teacher
    from app.models.duty import Duty
    from app.models.lesson import Lesson
    from app.models.substitution import Substitution
    from app.models.alert import Alert, AuditLog
    from app.models.attendance import TeacherAttendance
    from app.utils.days import normalize_day

    # secrets.token_urlsafe(16) = ~22 chars of URL-safe entropy, ≥128 bits.
    # Printed once to stdout so the operator can distribute credentials
    # out of band. The container log is the ONLY place these appear;
    # they are not returned in the API response, not stored in plaintext,
    # not reused across teachers.
    def _mkpw() -> str:
        return secrets.token_urlsafe(16)

    print("=" * 60, file=sys.stderr)
    print("SEED PASSWORDS — copy now, they are only printed once", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    db = SessionLocal()
    try:
        # Seed bootstrap check — legitimately cross-tenant: "does ANY user
        # exist anywhere?" prevents re-seeding into a populated database
        # regardless of tenant. Goes through cross_tenant_query so the
        # bypass is greppable in code review.
        from app.utils.tenant_query import cross_tenant_query
        if cross_tenant_query(
            db, User, reason="seed bootstrap: refuse if any user exists"
        ).count() > 0:
            return {"status": "already_seeded", "message": "Database already contains data"}

        # Admin — every user created by the seed must change password on
        # first login (must_change_password=True). No shared defaults.
        admin_email = "admin@eduschedule.com"
        admin_pw = _mkpw()
        print(f"  ADMIN  {admin_email:35}  {admin_pw}", file=sys.stderr)
        admin_id = cuid_lib.cuid()
        admin = User(id=admin_id, email=admin_email,
                     password=hash_password(admin_pw), name="Admin User", role="ADMIN",
                     must_change_password=True)
        db.add(admin)

        # 8 Teachers — (name, initials, dept, email, phone, quals, subjects, school_level)
        teachers_data = [
            ("Dr. Sarah Al-Rashid", "SAR", "Mathematics", "sarah@eduschedule.com", "+966501234567", ["MORNING_SUPERVISION", "EXAM_DUTY"], ["Mathematics", "Algebra"], "HIGH"),
            ("Mr. James Thornton", "JT", "English", "james@eduschedule.com", "+966501234568", ["LUNCH_SUPERVISION"], ["English", "Literature"], "MIDDLE"),
            ("Ms. Fatima Hassan", "FH", "Science", "fatima@eduschedule.com", "+966501234569", ["LAB_SUPERVISION", "EXAM_DUTY"], ["Science", "Biology"], "ELEMENTARY"),
            ("Mr. Ahmed Al-Mutairi", "AAM", "Arabic", "ahmed@eduschedule.com", "+966501234570", ["MORNING_SUPERVISION"], ["Arabic", "Islamic Studies"], "ELEMENTARY"),
            ("Ms. Priya Sharma", "PS", "Science", "priya@eduschedule.com", "+966501234571", ["EXAM_DUTY", "LAB_SUPERVISION"], ["Science", "Physics"], "HIGH"),
            ("Mr. Carlos Rivera", "CR", "History", "carlos@eduschedule.com", "+966501234572", ["LUNCH_SUPERVISION"], ["History", "Geography"], "MIDDLE"),
            ("Ms. Yuki Tanaka", "YT", "Mathematics", "yuki@eduschedule.com", "+966501234573", ["MORNING_SUPERVISION"], ["Mathematics", "Design"], "ELEMENTARY"),
            ("Mr. David Okafor", "DO", "PE", "david@eduschedule.com", "+966501234574", ["SPORTS_SUPERVISION", "LUNCH_SUPERVISION"], ["Physical Education", "Health"], "ALL"),
        ]

        teacher_ids = []
        for name, initials, dept, email, phone, quals, subjects, level in teachers_data:
            uid = cuid_lib.cuid()
            tid = cuid_lib.cuid()
            teacher_pw = _mkpw()
            print(f"  TEACH  {email:35}  {teacher_pw}", file=sys.stderr)
            u = User(id=uid, email=email, password=hash_password(teacher_pw),
                     name=name, role="TEACHER", must_change_password=True)
            t = Teacher(id=tid, user_id=uid, name=name, initials=initials, department=dept,
                        email=email, phone=phone, status="ACTIVE", max_duties=16,
                        qualifications=quals, subjects=subjects, school_level=level)
            db.add(u)
            db.add(t)
            teacher_ids.append(tid)
        print("=" * 60, file=sys.stderr)

        db.flush()

        # Canonical 3-letter day codes — normalize_day guards against a
        # future maintainer reintroducing long-form and re-breaking the
        # Substitutions filter bug (commit 27822f6).
        days = [normalize_day(d) for d in ("SUN", "MON", "TUE", "WED", "THU")]
        duty_defs = [
            ("MORNING_SUPERVISION", "ARRIVAL",    ("07:15", "07:45"), "Main Gate"),
            ("MORNING_SUPERVISION", "ARRIVAL",    ("07:30", "08:00"), "Side Entrance"),
            ("LUNCH_SUPERVISION",   "BREAK",      ("12:00", "12:30"), "Cafeteria"),
            ("LUNCH_SUPERVISION",   "BREAK",      ("12:30", "13:00"), "Corridor A"),
            ("EXAM_DUTY",           "EXAM",       ("09:00", "11:00"), "Exam Hall"),
            ("LAB_SUPERVISION",     "SUPERVISION",("10:00", "11:00"), "Lab 1"),
            ("SPORTS_SUPERVISION",  "SUPERVISION",("14:00", "15:00"), "Sports Court"),
            ("DISMISSAL_DUTY",      "DISMISSAL",  ("15:00", "15:30"), "Main Gate"),
        ]
        locations = ["Main Gate", "Corridor A", "Cafeteria", "Library", "Exam Hall", "Lab 1", "Lab 2", "Sports Court"]

        duty_ids = []
        for i in range(20):
            did = cuid_lib.cuid()
            day = days[i % 5]
            defn = duty_defs[i % len(duty_defs)]
            dtype, dcat, slot, loc = defn
            teacher_id = teacher_ids[i % 8] if i < 16 else None
            d = Duty(id=did, name=f"{dtype.replace('_', ' ').title()} - {loc}", type=dtype,
                     duty_category=dcat, day=day, start_time=slot[0], end_time=slot[1],
                     location=loc, teacher_id=teacher_id, status="CONFIRMED")
            db.add(d)
            duty_ids.append(did)

        # 30 Lessons — levels match teacher school_level
        teacher_levels = ["HIGH", "MIDDLE", "ELEMENTARY", "ELEMENTARY", "HIGH", "MIDDLE", "ELEMENTARY", "ALL"]
        subjects_map = ["Mathematics", "English", "Science", "Arabic", "Science", "History", "Mathematics", "Physical Education"]
        rooms = ["R101", "R102", "Lab1", "R201", "Lab2", "R202", "R103", "Gym"]
        lesson_slots = [("08:00", "09:00"), ("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00")]

        for i in range(30):
            t_idx = i % 8
            tid = teacher_ids[t_idx]
            day = days[i % 5]
            slot = lesson_slots[i % 4]
            subj = subjects_map[t_idx]
            room = rooms[t_idx]
            level = teacher_levels[t_idx]
            db.add(Lesson(id=cuid_lib.cuid(), teacher_id=tid, subject=subj,
                          class_=f"{10 + (i % 3)}{chr(65 + (i % 3))}", room=room,
                          day=day, start_time=slot[0], end_time=slot[1],
                          school_level=level))

        db.flush()

        db.add(Alert(id=cuid_lib.cuid(), severity="CRITICAL",
                     title="Scheduling Conflict", duty_id=duty_ids[4],
                     message="Dr. Sarah Al-Rashid has a lesson conflict on Friday at 09:00",
                     resolved=False))
        db.add(Alert(id=cuid_lib.cuid(), severity="HIGH",
                     title="Overloaded Teacher",
                     message="Mr. James Thornton has exceeded the recommended duty threshold",
                     duty_id=duty_ids[1], resolved=False))
        db.add(Alert(id=cuid_lib.cuid(), severity="MEDIUM",
                     title="Unassigned Duty",
                     message="Duty on Wednesday is missing a teacher assignment",
                     duty_id=duty_ids[10], resolved=False))

        # James Thornton — one absent attendance record for demo purposes.
        # Uses TeacherAttendance now that Absence has been consolidated.
        db.add(TeacherAttendance(
            id=cuid_lib.cuid(), teacher_id=teacher_ids[1],
            date=datetime(2026, 4, 14).date(),
            status="absent", note="Sick leave",
        ))
        db.add(Substitution(id=cuid_lib.cuid(), duty_id=duty_ids[1],
                             absent_teacher_id=teacher_ids[1], status="PENDING"))

        entries = [
            ("SCHEDULE_UPDATED", "Admin User", "Schedule updated for Week 15"),
            ("DUTY_ASSIGNED", "Admin User", "Dr. Sarah Al-Rashid assigned to Morning Supervision"),
            ("TEACHER_CREATED", "Admin User", "New teacher Ms. Yuki Tanaka added to system"),
            ("ALERT_RESOLVED", "Admin User", "Resolved medium priority unassigned duty alert"),
            ("SUBSTITUTION_REQUESTED", "System", "Substitution requested for James Thornton - Lunch Supervision"),
        ]
        for action, actor, details in entries:
            db.add(AuditLog(id=cuid_lib.cuid(), action=action, actor=actor, details=details))

        db.commit()
        return {
            "status": "ok",
            "seeded": {
                "users": 9,
                "teachers": 8,
                "duties": 20,
                "lessons": 30,
                "alerts": 3,
                "substitutions": 1,
                "audit_logs": 5,
            }
        }
    except Exception as e:
        db.rollback()
        logger.exception("Seed failed")
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")
    finally:
        db.close()
