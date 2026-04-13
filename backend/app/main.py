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


@app.post("/api/admin/seed")
def seed_database(x_seed_key: str = Header(...)):
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
        # Check if already seeded
        if db.query(User).count() > 0:
            return {"status": "already_seeded", "message": "Database already contains data"}

        # Admin user
        admin_id = cuid_lib.cuid()
        admin = User(id=admin_id, email="admin@eduschedule.com",
                     password=hash_password("Admin@123"), name="Admin User", role="ADMIN")
        db.add(admin)

        # 8 Teachers
        teachers_data = [
            ("Dr. Sarah Al-Rashid", "SAR", "Mathematics", "sarah@eduschedule.com", "+966501234567", ["MORNING_SUPERVISION", "EXAM_DUTY"], ["Calculus", "Algebra"]),
            ("Mr. James Thornton", "JT", "English", "james@eduschedule.com", "+966501234568", ["LUNCH_SUPERVISION"], ["Literature", "Grammar"]),
            ("Ms. Fatima Hassan", "FH", "Science", "fatima@eduschedule.com", "+966501234569", ["LAB_SUPERVISION", "EXAM_DUTY"], ["Biology", "Chemistry"]),
            ("Mr. Ahmed Al-Mutairi", "AAM", "Arabic", "ahmed@eduschedule.com", "+966501234570", ["MORNING_SUPERVISION"], ["Arabic Language", "Islamic Studies"]),
            ("Ms. Priya Sharma", "PS", "Physics", "priya@eduschedule.com", "+966501234571", ["EXAM_DUTY", "LAB_SUPERVISION"], ["Physics", "Mathematics"]),
            ("Mr. Carlos Rivera", "CR", "History", "carlos@eduschedule.com", "+966501234572", ["LUNCH_SUPERVISION"], ["World History", "Geography"]),
            ("Ms. Yuki Tanaka", "YT", "Art", "yuki@eduschedule.com", "+966501234573", ["MORNING_SUPERVISION"], ["Fine Arts", "Design"]),
            ("Mr. David Okafor", "DO", "PE", "david@eduschedule.com", "+966501234574", ["SPORTS_SUPERVISION", "LUNCH_SUPERVISION"], ["Physical Education", "Health"]),
        ]

        teacher_ids = []
        for name, initials, dept, email, phone, quals, subjects in teachers_data:
            uid = cuid_lib.cuid()
            tid = cuid_lib.cuid()
            u = User(id=uid, email=email, password=hash_password("Teacher@123"), name=name, role="TEACHER")
            t = Teacher(id=tid, user_id=uid, name=name, initials=initials, department=dept,
                        email=email, phone=phone, status="ACTIVE", max_duties=16,
                        qualifications=quals, subjects=subjects)
            db.add(u)
            db.add(t)
            teacher_ids.append(tid)

        db.flush()

        # 20 Duties
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
        duty_types = ["MORNING_SUPERVISION", "LUNCH_SUPERVISION", "EXAM_DUTY", "LAB_SUPERVISION"]
        slots = [("07:30", "08:00"), ("08:00", "08:30"), ("12:00", "12:30"), ("12:30", "13:00")]
        locations = ["Main Gate", "Corridor A", "Cafeteria", "Library", "Exam Hall", "Lab 1", "Lab 2", "Sports Court"]

        duty_ids = []
        for i in range(20):
            did = cuid_lib.cuid()
            day = days[i % 5]
            dtype = duty_types[i % 4]
            slot = slots[i % 4]
            loc = locations[i % 8]
            teacher_id = teacher_ids[i % 8] if i < 16 else None
            d = Duty(id=did, name=f"{dtype.replace('_', ' ').title()} - {loc}", type=dtype,
                     day=day, start_time=slot[0], end_time=slot[1], location=loc,
                     teacher_id=teacher_id, status="CONFIRMED")
            db.add(d)
            duty_ids.append(did)

        # 30 Lessons
        subjects_map = ["Mathematics", "English", "Science", "Arabic", "Physics", "History", "Art", "PE"]
        rooms = ["R101", "R102", "R201", "R202", "Lab1", "Hall", "Studio", "Gym"]
        lesson_slots = [("08:00", "09:00"), ("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00")]

        for i in range(30):
            tid = teacher_ids[i % 8]
            day = days[i % 5]
            slot = lesson_slots[i % 4]
            subj = subjects_map[i % 8]
            room = rooms[i % 8]
            db.add(Lesson(id=cuid_lib.cuid(), teacher_id=tid, subject=subj,
                          class_=f"{10 + (i % 3)}{chr(65 + (i % 3))}", room=room,
                          day=day, start_time=slot[0], end_time=slot[1]))

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
