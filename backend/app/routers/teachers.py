import cuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.middleware.auth import get_current_user, hash_password
from app.models.teacher import User, Teacher
from app.models.duty import Duty
from app.models.alert import Absence, AuditLog
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse
from typing import Optional

router = APIRouter()


def _make_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _teacher_to_response(t: Teacher) -> dict:
    duty_count = len(t.duties) if t.duties else 0
    workload_pct = round((duty_count / (t.max_duties or 16)) * 100, 1)
    return {
        "id": t.id,
        "name": t.name,
        "initials": t.initials,
        "department": t.department,
        "email": t.email,
        "phone": t.phone,
        "status": t.status,
        "max_duties": t.max_duties,
        "qualifications": t.qualifications or [],
        "subjects": t.subjects or [],
        "duty_count": duty_count,
        "workload_pct": workload_pct,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("/")
def list_teachers(db: Session = Depends(get_db), _=Depends(get_current_user)):
    teachers = (
        db.query(Teacher)
        .filter(Teacher.status != "INACTIVE")
        .options(joinedload(Teacher.duties))
        .all()
    )
    return {"teachers": [_teacher_to_response(t) for t in teachers], "total": len(teachers)}


@router.post("/", status_code=201)
def create_teacher(
    data: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Teacher).filter(Teacher.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=cuid.cuid(),
        email=data.email,
        password=hash_password(data.password),
        name=data.name,
        role="TEACHER",
    )
    db.add(user)
    db.flush()
    teacher = Teacher(
        id=cuid.cuid(),
        user_id=user.id,
        name=data.name,
        initials=_make_initials(data.name),
        department=data.department,
        email=data.email,
        phone=data.phone,
        status=data.status,
        max_duties=data.max_duties,
        qualifications=data.qualifications,
        subjects=data.subjects,
    )
    db.add(teacher)
    db.add(AuditLog(id=cuid.cuid(), action="CREATE_TEACHER", actor=current_user.email, details=f"Created teacher {data.name}"))
    db.commit()
    db.refresh(teacher)
    return _teacher_to_response(teacher)


@router.get("/{teacher_id}")
def get_teacher(teacher_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    teacher = (
        db.query(Teacher)
        .filter(Teacher.id == teacher_id)
        .options(
            joinedload(Teacher.duties),
            joinedload(Teacher.lessons),
            joinedload(Teacher.absences),
        )
        .first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    result = _teacher_to_response(teacher)
    result["lessons"] = [
        {
            "id": l.id, "subject": l.subject, "class": l.class_,
            "room": l.room, "day": l.day, "start_time": l.start_time, "end_time": l.end_time,
        }
        for l in (teacher.lessons or [])
    ]
    result["duties"] = [
        {
            "id": d.id, "name": d.name, "type": d.type, "day": d.day,
            "start_time": d.start_time, "end_time": d.end_time,
            "location": d.location, "status": d.status,
        }
        for d in (teacher.duties or [])
    ]
    result["absences"] = [
        {"id": a.id, "date": a.date, "reason": a.reason}
        for a in (teacher.absences or [])
    ]
    return result


@router.put("/{teacher_id}")
def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(teacher, field, value)
    db.add(AuditLog(id=cuid.cuid(), action="UPDATE_TEACHER", actor=current_user.email, details=f"Updated teacher {teacher.name}"))
    db.commit()
    db.refresh(teacher)
    return _teacher_to_response(teacher)


@router.delete("/{teacher_id}", status_code=204)
def delete_teacher(
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.status = "INACTIVE"
    db.add(AuditLog(id=cuid.cuid(), action="DELETE_TEACHER", actor=current_user.email, details=f"Deactivated teacher {teacher.name}"))
    db.commit()


@router.post("/{teacher_id}/absent")
def mark_absent(
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    teacher.status = "ABSENT"
    absence = Absence(
        id=cuid.cuid(),
        teacher_id=teacher_id,
        date=datetime.now(timezone.utc),
        reason="Marked absent by admin",
    )
    db.add(absence)
    db.add(AuditLog(id=cuid.cuid(), action="MARK_ABSENT", actor=current_user.email, details=f"Marked {teacher.name} as absent"))
    db.commit()
    return {"message": f"{teacher.name} marked absent"}


@router.get("/{teacher_id}/schedule")
def teacher_schedule(teacher_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.models.lesson import Lesson
    from app.routers.schedule import build_teacher_week_grid
    return build_teacher_week_grid(teacher_id, db)
