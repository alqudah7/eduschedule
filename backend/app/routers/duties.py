import cuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import User, Teacher
from app.models.duty import Duty
from app.models.lesson import Lesson
from app.models.alert import AuditLog, Alert
from app.schemas.duty import DutyCreate, DutyUpdate
from app.services.conflict_engine import ConflictEngine, TimeSlot
from app.utils.audit import write_audit_log
from app.utils.days import normalize_day

router = APIRouter()


def _run_conflict_check(duty: Duty, db: Session, school_id: int) -> list[TimeSlot]:
    """Find conflicts for `duty`. Every DB read is tenant-scoped —
    conflicts across tenants would be nonsensical (and a data leak)."""
    if not duty.teacher_id:
        return []
    all_duties = db.query(Duty).filter(
        Duty.school_id == school_id,
        Duty.teacher_id == duty.teacher_id,
        Duty.day == duty.day,
        Duty.id != duty.id,
        Duty.status != "CANCELLED",
    ).all()
    all_lessons = db.query(Lesson).filter(
        Lesson.school_id == school_id,
        Lesson.teacher_id == duty.teacher_id,
        Lesson.day == duty.day,
    ).all()

    target = TimeSlot(
        day=duty.day,
        start_time=duty.start_time,
        end_time=duty.end_time,
        teacher_id=duty.teacher_id,
        label=duty.name,
        record_id=duty.id,
        record_type="duty",
    )
    all_slots = [
        TimeSlot(day=d.day, start_time=d.start_time, end_time=d.end_time,
                 teacher_id=d.teacher_id, label=d.name, record_id=d.id, record_type="duty")
        for d in all_duties
    ] + [
        TimeSlot(day=l.day, start_time=l.start_time, end_time=l.end_time,
                 teacher_id=l.teacher_id, label=l.subject, record_id=l.id, record_type="lesson")
        for l in all_lessons
    ]
    return ConflictEngine.find_conflicts(target, all_slots)


def _duty_to_dict(d: Duty) -> dict:
    result = {
        "id": d.id, "name": d.name, "type": d.type, "day": d.day,
        "start_time": d.start_time, "end_time": d.end_time,
        "location": d.location, "teacher_id": d.teacher_id,
        "duty_category": getattr(d, "duty_category", "SUPERVISION") or "SUPERVISION",
        "status": d.status, "notes": d.notes,
        "created_at": d.created_at, "updated_at": d.updated_at,
    }
    if d.teacher:
        result["teacher"] = {
            "id": d.teacher.id, "name": d.teacher.name,
            "initials": d.teacher.initials, "department": d.teacher.department,
        }
    return result


@router.get("/")
def list_duties(
    day: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Duty).options(joinedload(Duty.teacher)).filter(
        Duty.school_id == current_user.school_id,
    )
    if day:
        q = q.filter(Duty.day == normalize_day(day))
    if status:
        q = q.filter(Duty.status == status)
    if type:
        q = q.filter(Duty.type == type)
    duties = q.all()
    return {"duties": [_duty_to_dict(d) for d in duties], "total": len(duties)}


@router.post("/", status_code=201)
def create_duty(
    data: DutyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = Duty(
        id=cuid.cuid(), name=data.name, type=data.type, day=data.day,
        start_time=data.start_time, end_time=data.end_time,
        location=data.location, teacher_id=data.teacher_id,
        duty_category=data.duty_category or "SUPERVISION",
        status="CONFIRMED", notes=data.notes,
        school_id=current_user.school_id,
    )
    db.add(duty)
    db.flush()

    conflicts = _run_conflict_check(duty, db, current_user.school_id)
    if conflicts:
        duty.status = "CONFLICT"
        conflict_labels = ", ".join(c.label for c in conflicts)
        # teacher lookup is scoped so we cannot accidentally reference a
        # teacher from another school in the alert body.
        teacher = db.query(Teacher).filter(
            Teacher.school_id == current_user.school_id,
            Teacher.id == duty.teacher_id,
        ).first()
        alert = Alert(
            id=cuid.cuid(), severity="CRITICAL",
            title=f"Scheduling Conflict: {duty.name}",
            message=f"Duty '{duty.name}' conflicts with: {conflict_labels}",
            duty_id=duty.id, resolved=False,
            school_id=current_user.school_id,
        )
        db.add(alert)

    write_audit_log(db, actor=current_user, action="CREATE_DUTY",
                    details=f"Created duty {data.name}")
    db.commit()
    db.refresh(duty)
    return _duty_to_dict(duty)


@router.get("/{duty_id}")
def get_duty(
    duty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = db.query(Duty).options(joinedload(Duty.teacher)).filter(
        Duty.school_id == current_user.school_id,
        Duty.id == duty_id,
    ).first()
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    return _duty_to_dict(duty)


@router.put("/{duty_id}")
def update_duty(
    duty_id: str,
    data: DutyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = db.query(Duty).options(joinedload(Duty.teacher)).filter(
        Duty.school_id == current_user.school_id,
        Duty.id == duty_id,
    ).first()
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(duty, field, value)
    db.flush()
    conflicts = _run_conflict_check(duty, db, current_user.school_id)
    if conflicts and duty.status != "CANCELLED":
        duty.status = "CONFLICT"
    elif not conflicts and duty.status == "CONFLICT":
        duty.status = "CONFIRMED"
    write_audit_log(db, actor=current_user, action="UPDATE_DUTY",
                    details=f"Updated duty {duty.name}")
    db.commit()
    db.refresh(duty)
    return _duty_to_dict(duty)


@router.delete("/{duty_id}", status_code=204)
def delete_duty(
    duty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = db.query(Duty).filter(
        Duty.school_id == current_user.school_id,
        Duty.id == duty_id,
    ).first()
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    db.delete(duty)
    write_audit_log(db, actor=current_user, action="DELETE_DUTY",
                    details=f"Deleted duty {duty.name}")
    db.commit()


@router.post("/{duty_id}/resolve-conflict")
def resolve_conflict(
    duty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duty = db.query(Duty).filter(
        Duty.school_id == current_user.school_id,
        Duty.id == duty_id,
    ).first()
    if not duty:
        raise HTTPException(status_code=404, detail="Duty not found")
    duty.status = "CONFIRMED"
    alerts = db.query(Alert).filter(
        Alert.school_id == current_user.school_id,
        Alert.duty_id == duty_id,
        Alert.resolved == False,
    ).all()
    for a in alerts:
        a.resolved = True
    write_audit_log(db, actor=current_user, action="RESOLVE_CONFLICT",
                    details=f"Resolved conflict for duty {duty.name}")
    db.commit()
    return {"message": "Conflict resolved"}
