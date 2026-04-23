import cuid, csv, io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import Teacher
from app.models.duty import Duty
from app.models.lesson import Lesson

router = APIRouter()

DAYS = ["SUN", "MON", "TUE", "WED", "THU"]


def build_teacher_week_grid(teacher_id: str, db: Session) -> dict:
    lessons = db.query(Lesson).filter(Lesson.teacher_id == teacher_id).all()
    duties = db.query(Duty).filter(Duty.teacher_id == teacher_id).all()

    grid: dict = {day: {} for day in DAYS}

    for lesson in lessons:
        slot_key = lesson.start_time
        cell = {
            "type": "lesson",
            "lesson": {
                "id": lesson.id, "subject": lesson.subject,
                "class": lesson.class_, "room": lesson.room,
                "start_time": lesson.start_time, "end_time": lesson.end_time,
                "school_level": getattr(lesson, "school_level", "ALL") or "ALL",
            },
        }
        grid[lesson.day][slot_key] = cell

    for duty in duties:
        slot_key = duty.start_time
        cell_type = "conflict" if duty.status == "CONFLICT" else "duty"
        existing = grid.get(duty.day, {}).get(slot_key)
        if existing:
            cell_type = "conflict"
        grid[duty.day][slot_key] = {
            "type": cell_type,
            "duty": {
                "id": duty.id, "name": duty.name, "type": duty.type,
                "location": duty.location, "start_time": duty.start_time,
                "end_time": duty.end_time, "status": duty.status,
                "duty_category": getattr(duty, "duty_category", "SUPERVISION") or "SUPERVISION",
            },
        }

    return {"teacher_id": teacher_id, "grid": grid}


@router.get("/week")
def full_week(db: Session = Depends(get_db), _=Depends(get_current_user)):
    teachers = db.query(Teacher).filter(Teacher.status != "INACTIVE").all()
    result = []
    for t in teachers:
        grid_data = build_teacher_week_grid(t.id, db)
        result.append({
            "teacher": {"id": t.id, "name": t.name, "initials": t.initials, "department": t.department},
            "grid": grid_data["grid"],
        })
    return {"teachers": result}


@router.get("/teacher/{teacher_id}/week")
def teacher_week(teacher_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return build_teacher_week_grid(teacher_id, db)


@router.post("/import")
async def import_schedule(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    imported, skipped, errors = 0, 0, []

    for i, row in enumerate(reader):
        row_num = i + 2
        try:
            email = (row.get("teacher_email") or "").strip().lower()
            teacher = db.query(Teacher).filter(Teacher.email == email).first()
            if not teacher:
                skipped += 1
                errors.append({"row": row_num, "reason": f"Teacher '{email}' not found — import teachers first"})
                continue
            lesson = Lesson(
                id=cuid.cuid(), teacher_id=teacher.id,
                subject=row["subject"], class_=row["class"],
                room=row["room"], day=row["day"].upper(),
                start_time=row["start_time"], end_time=row["end_time"],
                school_level=(row.get("school_level") or "ALL").upper(),
            )
            db.add(lesson)
            imported += 1
        except Exception as e:
            errors.append({"row": row_num, "reason": str(e)})

    db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}
