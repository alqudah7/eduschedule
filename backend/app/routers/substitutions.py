import cuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import User, Teacher
from app.models.duty import Duty
from app.models.substitution import Substitution
from app.models.alert import AuditLog
from app.services.fairness_engine import FairnessEngine
from app.services.notification_service import NotificationService

router = APIRouter()


def _duty_qual(duty_type: str) -> str:
    mapping = {
        "SUPERVISION": "general",
        "EXAM": "exam",
        "LIBRARY": "library",
        "SPORTS": "sports",
        "EXTRACURRICULAR": "general",
    }
    return mapping.get(duty_type, "general")


def _sub_to_dict(s: Substitution) -> dict:
    result = {
        "id": s.id, "duty_id": s.duty_id, "absent_teacher_id": s.absent_teacher_id,
        "substitute_id": s.substitute_id, "status": s.status,
        "requested_at": s.requested_at, "resolved_at": s.resolved_at, "notes": s.notes,
    }
    if s.absent_teacher:
        result["absent_teacher"] = {
            "id": s.absent_teacher.id, "name": s.absent_teacher.name,
            "initials": s.absent_teacher.initials, "department": s.absent_teacher.department,
        }
    if s.substitute:
        result["substitute"] = {
            "id": s.substitute.id, "name": s.substitute.name,
            "initials": s.substitute.initials,
        }
    if s.duty:
        result["duty"] = {
            "id": s.duty.id, "name": s.duty.name, "type": s.duty.type,
            "day": s.duty.day, "start_time": s.duty.start_time, "end_time": s.duty.end_time,
            "location": s.duty.location, "status": s.duty.status,
        }
    return result


@router.get("/")
def list_substitutions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Substitution).options(
        joinedload(Substitution.duty),
        joinedload(Substitution.absent_teacher),
        joinedload(Substitution.substitute),
    )
    if status:
        q = q.filter(Substitution.status == status)
    subs = q.all()
    return {"substitutions": [_sub_to_dict(s) for s in subs], "total": len(subs)}


@router.post("/", status_code=201)
def create_substitution(
    duty_id: str,
    absent_teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = Substitution(
        id=cuid.cuid(), duty_id=duty_id, absent_teacher_id=absent_teacher_id, status="PENDING",
    )
    db.add(sub)
    duty = db.query(Duty).filter(Duty.id == duty_id).first()
    if duty:
        duty.status = "SUBSTITUTE_NEEDED"
    db.add(AuditLog(id=cuid.cuid(), action="CREATE_SUB_REQUEST", actor=current_user.email,
                    details=f"Sub request created for duty {duty_id}"))
    db.commit()
    db.refresh(sub)
    return _sub_to_dict(sub)


@router.get("/{sub_id}/suggestions")
def get_suggestions(sub_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    sub = db.query(Substitution).options(joinedload(Substitution.duty)).filter(Substitution.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution not found")
    teachers = db.query(Teacher).options(joinedload(Teacher.duties)).filter(Teacher.status == "ACTIVE").all()
    required_qual = _duty_qual(sub.duty.type if sub.duty else "SUPERVISION")
    ranked = FairnessEngine.rank_substitutes(teachers, required_qual, sub.absent_teacher_id)
    return {
        "suggestions": [
            {
                "teacher": {
                    "id": r["teacher"].id, "name": r["teacher"].name,
                    "initials": r["teacher"].initials, "department": r["teacher"].department,
                    "qualifications": r["teacher"].qualifications or [],
                },
                "load_pct": r["load_pct"],
                "score": r["score"],
            }
            for r in ranked
        ]
    }


@router.post("/{sub_id}/assign")
def assign_substitute(
    sub_id: str,
    substitute_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(Substitution).options(
        joinedload(Substitution.duty), joinedload(Substitution.absent_teacher),
    ).filter(Substitution.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution not found")
    substitute = db.query(Teacher).filter(Teacher.id == substitute_id).first()
    if not substitute:
        raise HTTPException(status_code=404, detail="Substitute teacher not found")
    sub.substitute_id = substitute_id
    sub.status = "ACCEPTED"
    sub.resolved_at = datetime.now(timezone.utc)
    if sub.duty:
        sub.duty.status = "CONFIRMED"
        sub.duty.teacher_id = substitute_id
    duty_time = f"{sub.duty.start_time}–{sub.duty.end_time}" if sub.duty else ""
    duty_name = sub.duty.name if sub.duty else "duty"
    background_tasks.add_task(
        NotificationService.send_substitution_request,
        substitute.email, substitute.name, duty_name, duty_time,
    )
    db.add(AuditLog(id=cuid.cuid(), action="ASSIGN_SUBSTITUTE", actor=current_user.email,
                    details=f"Assigned {substitute.name} to {duty_name}"))
    db.commit()
    return {"message": "Substitute assigned", "substitute": substitute.name}


@router.post("/{sub_id}/accept")
def accept_sub(sub_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sub = db.query(Substitution).filter(Substitution.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    sub.status = "ACCEPTED"
    sub.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Accepted"}


@router.post("/{sub_id}/decline")
def decline_sub(sub_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sub = db.query(Substitution).filter(Substitution.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    sub.status = "DECLINED"
    sub.substitute_id = None
    db.commit()
    return {"message": "Declined"}
