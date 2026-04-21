from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.routers import auth, teachers, duties, schedule, substitutions, alerts, reports

# Import all models so Base.metadata knows about them before create_all
import app.models.teacher  # noqa: F401
import app.models.duty  # noqa: F401
import app.models.lesson  # noqa: F401
import app.models.substitution  # noqa: F401
import app.models.alert  # noqa: F401

app = FastAPI(title="EduSchedule API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(teachers.router, prefix="/api/teachers", tags=["teachers"])
app.include_router(duties.router, prefix="/api/duties", tags=["duties"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(substitutions.router, prefix="/api/substitutions", tags=["substitutions"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    _run_column_migrations()


def _run_column_migrations():
    """Add new columns to existing tables without dropping data."""
    from sqlalchemy import text
    migrations = [
        'ALTER TABLE "Teacher" ADD COLUMN IF NOT EXISTS "schoolLevel" VARCHAR DEFAULT \'ALL\'',
        'ALTER TABLE "Lesson"  ADD COLUMN IF NOT EXISTS "schoolLevel" VARCHAR DEFAULT \'ALL\'',
        'ALTER TABLE "Duty"    ADD COLUMN IF NOT EXISTS "dutyCategory" VARCHAR DEFAULT \'SUPERVISION\'',
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
        conn.commit()


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/admin/debug-auth")
def debug_auth():
    """Test bcrypt/passlib availability (no sensitive data)."""
    import traceback
    try:
        from app.middleware.auth import hash_password, verify_password
        h = hash_password("testpassword")
        ok = verify_password("testpassword", h)
        return {"bcrypt": "ok", "hash_len": len(h), "verify": ok}
    except Exception as e:
        return {"bcrypt": "error", "detail": str(e), "trace": traceback.format_exc()}


@app.post("/api/admin/debug-login")
def debug_login(email: str, password: str):
    """Debug login — exposes error details. Remove after debugging."""
    import traceback
    from app.models.teacher import User
    from app.middleware.auth import verify_password, create_access_token
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"step": "user_lookup", "error": f"No user found for email: {email}"}
        try:
            ok = verify_password(password, user.password)
        except Exception as e:
            return {"step": "verify_password", "error": str(e), "trace": traceback.format_exc()}
        if not ok:
            return {"step": "verify_password", "error": "password mismatch"}
        try:
            token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
        except Exception as e:
            return {"step": "create_token", "error": str(e), "trace": traceback.format_exc()}
        return {"step": "ok", "token_prefix": token[:20]}
    finally:
        db.close()


@app.post("/api/admin/seed")
def seed_database(x_seed_key: str = Header(...), force: bool = False):
    """Seed the database with initial data. Protected by X-Seed-Key header matching JWT_SECRET."""
    if x_seed_key != settings.SEED_KEY:
        raise HTTPException(status_code=403, detail="Invalid seed key")

    import cuid as cuid_lib
    from app.middleware.auth import hash_password
    from app.models.teacher import User, Teacher
    from app.models.duty import Duty
    from app.models.lesson import Lesson
    from app.models.substitution import Substitution
    from app.models.alert import Alert, Absence, AuditLog
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        # Check if already seeded (skip if force=true)
        if db.query(User).count() > 0:
            if not force:
                return {"status": "already_seeded", "message": "Database already contains data"}
            # Wipe existing data in dependency order
            db.query(AuditLog).delete()
            db.query(Absence).delete()
            db.query(Alert).delete()
            db.query(Substitution).delete()
            db.query(Lesson).delete()
            db.query(Duty).delete()
            db.query(Teacher).delete()
            db.query(User).delete()
            db.commit()

        # Admin user
        admin_id = cuid_lib.cuid()
        admin = User(id=admin_id, email="admin@eduschedule.com",
                     password=hash_password("Admin@123"), name="Admin User", role="ADMIN")
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
            u = User(id=uid, email=email, password=hash_password("Teacher@123"), name=name, role="TEACHER")
            t = Teacher(id=tid, user_id=uid, name=name, initials=initials, department=dept,
                        email=email, phone=phone, status="ACTIVE", max_duties=16,
                        qualifications=quals, subjects=subjects, school_level=level)
            db.add(u)
            db.add(t)
            teacher_ids.append(tid)

        db.flush()

        # 20 Duties — (type, category, slot, location)
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
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
        # teacher_ids index → level: [HIGH, MIDDLE, ELEMENTARY, ELEMENTARY, HIGH, MIDDLE, ELEMENTARY, ALL]
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

        # 1 conflict alert (Sarah teaching + duty at same time Friday 09:00)
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

        # 1 Absence + Substitution request (James Thornton absent)
        absence_id = cuid_lib.cuid()
        db.add(Absence(id=absence_id, teacher_id=teacher_ids[1],
                       date=datetime(2026, 4, 14, 0, 0, tzinfo=timezone.utc), reason="Sick leave"))
        db.add(Substitution(id=cuid_lib.cuid(), duty_id=duty_ids[1],
                             absent_teacher_id=teacher_ids[1], status="PENDING"))

        # 5 Audit log entries
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
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")
    finally:
        db.close()
