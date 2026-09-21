import cuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import User, Teacher
from app.models.duty import Duty
from app.models.lesson import Lesson
from app.models.substitution import Substitution
from app.models.alert import AuditLog
from app.services.day_planner import Availability, DayPlanner
from app.services.fairness_engine import FairnessEngine
from app.services.substitution_engine import SubstitutionEngine
from app.services.notification_service import NotificationService
from app.utils.audit import write_audit_log
from app.utils.days import normalize_day

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
        "id": s.id, "duty_id": s.duty_id, "lesson_id": s.lesson_id,
        "absent_teacher_id": s.absent_teacher_id,
        "substitute_id": s.substitute_id, "status": s.status,
        "requested_at": s.requested_at, "resolved_at": s.resolved_at, "notes": s.notes,
        "sub_type": "lesson" if s.lesson_id else "duty",
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
    if s.lesson:
        result["lesson"] = {
            "id": s.lesson.id, "subject": s.lesson.subject, "class": s.lesson.class_,
            "room": s.lesson.room, "day": s.lesson.day,
            "start_time": s.lesson.start_time, "end_time": s.lesson.end_time,
            "school_level": s.lesson.school_level,
        }
    return result


@router.get("/")
def list_substitutions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Substitution).options(
        joinedload(Substitution.duty),
        joinedload(Substitution.lesson),
        joinedload(Substitution.absent_teacher),
        joinedload(Substitution.substitute),
    ).filter(Substitution.school_id == current_user.school_id)
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
        school_id=current_user.school_id,
    )
    db.add(sub)
    duty = db.query(Duty).filter(
        Duty.school_id == current_user.school_id,
        Duty.id == duty_id,
    ).first()
    if duty:
        duty.status = "SUBSTITUTE_NEEDED"
    write_audit_log(db, actor=current_user, action="CREATE_SUB_REQUEST",
                    details=f"Sub request created for duty {duty_id}")
    db.commit()
    db.refresh(sub)
    return _sub_to_dict(sub)


@router.get("/{sub_id}/suggestions")
def get_suggestions(
    sub_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(Substitution).options(
        joinedload(Substitution.duty),
        joinedload(Substitution.absent_teacher),
    ).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution not found")

    absent_teacher = db.query(Teacher).options(
        joinedload(Teacher.duties),
        joinedload(Teacher.lessons),
    ).filter(
        Teacher.school_id == current_user.school_id,
        Teacher.id == sub.absent_teacher_id,
    ).first()

    if not absent_teacher:
        raise HTTPException(status_code=404, detail="Absent teacher not found")

    duty = sub.duty
    if not duty:
        raise HTTPException(status_code=400, detail="Substitution has no associated duty")

    teachers = db.query(Teacher).options(
        joinedload(Teacher.duties),
        joinedload(Teacher.lessons),
    ).filter(
        Teacher.school_id == current_user.school_id,
        Teacher.status == "ACTIVE",
    ).all()

    ranked = SubstitutionEngine.rank_substitutes(
        teachers=teachers,
        absent_teacher=absent_teacher,
        day=duty.day,
        start_time=duty.start_time,
        end_time=duty.end_time,
    )

    return {
        "suggestions": [
            {
                "teacher": {
                    "id": r["teacher"].id,
                    "name": r["teacher"].name,
                    "initials": r["teacher"].initials,
                    "department": r["teacher"].department,
                    "qualifications": r["teacher"].qualifications or [],
                    "subjects": r["teacher"].subjects or [],
                    "school_level": getattr(r["teacher"], "school_level", "ALL"),
                },
                "load_pct": r["load_pct"],
                "score": r["score"],
                "tier": r["tier"],
                "tier_label": r["tier_label"],
                "subject_match": r["subject_match"],
                "level_match": r["level_match"],
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
    ).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution not found")
    substitute = db.query(Teacher).filter(
        Teacher.school_id == current_user.school_id,
        Teacher.id == substitute_id,
    ).first()
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
    write_audit_log(db, actor=current_user, action="ASSIGN_SUBSTITUTE",
                    details=f"Assigned {substitute.name} to {duty_name}")
    db.commit()
    return {"message": "Substitute assigned", "substitute": substitute.name}


@router.post("/{sub_id}/accept")
def accept_sub(
    sub_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(Substitution).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    sub.status = "ACCEPTED"
    sub.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Accepted"}


@router.post("/{sub_id}/decline")
def decline_sub(
    sub_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(Substitution).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    sub.status = "DECLINED"
    sub.substitute_id = None
    db.commit()
    return {"message": "Declined"}


# ─── Lesson substitution endpoints ───────────────────────────────────────────

@router.get("/absent-lessons")
def get_absent_teacher_lessons(
    teacher_id: str = Query(...),
    day: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all lessons for a teacher on a given day, with sub-request status."""
    day_norm = normalize_day(day)
    lessons = (
        db.query(Lesson)
        .filter(
            Lesson.school_id == current_user.school_id,
            Lesson.teacher_id == teacher_id,
            Lesson.day == day_norm,
        )
        .order_by(Lesson.start_time)
        .all()
    )
    # Map lesson_id → existing substitution
    lesson_ids = [l.id for l in lessons]
    existing_subs = (
        db.query(Substitution)
        .filter(
            Substitution.school_id == current_user.school_id,
            Substitution.lesson_id.in_(lesson_ids),
        )
        .all()
    ) if lesson_ids else []
    sub_map = {s.lesson_id: s for s in existing_subs}

    result = []
    for lesson in lessons:
        sub = sub_map.get(lesson.id)
        result.append({
            "id": lesson.id,
            "subject": lesson.subject,
            "class": lesson.class_,
            "room": lesson.room,
            "day": lesson.day,
            "start_time": lesson.start_time,
            "end_time": lesson.end_time,
            "school_level": lesson.school_level,
            "substitution": _sub_to_dict(sub) if sub else None,
        })
    return {"lessons": result, "total": len(result)}


@router.post("/lesson", status_code=201)
def create_lesson_substitution(
    lesson_id: str,
    absent_teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a substitution request for a lesson (class cover)."""
    lesson = db.query(Lesson).filter(
        Lesson.school_id == current_user.school_id,
        Lesson.id == lesson_id,
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    # Prevent duplicate requests
    existing = db.query(Substitution).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.lesson_id == lesson_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Substitution request already exists for this lesson")
    sub = Substitution(
        id=cuid.cuid(),
        lesson_id=lesson_id,
        absent_teacher_id=absent_teacher_id,
        status="PENDING",
        school_id=current_user.school_id,
    )
    db.add(sub)
    write_audit_log(
        db, actor=current_user, action="CREATE_LESSON_SUB",
        details=f"Lesson sub requested: {lesson.subject} {lesson.class_} on {lesson.day}",
    )
    db.commit()
    db.refresh(sub)
    # Load relationships for response
    sub = db.query(Substitution).options(
        joinedload(Substitution.lesson),
        joinedload(Substitution.absent_teacher),
    ).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub.id,
    ).first()
    return _sub_to_dict(sub)


@router.get("/{sub_id}/lesson-suggestions")
def get_lesson_suggestions(
    sub_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ranked list of available teachers who can cover this lesson."""
    sub = db.query(Substitution).options(
        joinedload(Substitution.lesson),
        joinedload(Substitution.absent_teacher),
    ).filter(
        Substitution.school_id == current_user.school_id,
        Substitution.id == sub_id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution not found")
    if not sub.lesson:
        raise HTTPException(status_code=400, detail="This is not a lesson substitution")

    lesson = sub.lesson
    teachers = db.query(Teacher).options(
        joinedload(Teacher.duties),
        joinedload(Teacher.lessons),
    ).filter(
        Teacher.school_id == current_user.school_id,
        Teacher.status == "ACTIVE",
    ).all()

    from app.services.free_period_engine import FreePeriodEngine

    lesson_subjects = {lesson.subject.lower()}
    lesson_level = lesson.school_level or "ALL"

    # Level adjacency was duplicated with substitution_engine.LEVEL_CHAIN
    # (AUDIT.md flagged this). Use the shared source of truth from the
    # engine instead of a second inline table.
    from app.services.substitution_engine import LEVEL_CHAIN

    def level_matches(teacher_level: str) -> bool:
        """True when teacher can teach at the lesson's school level."""
        if lesson_level == "ALL" or teacher_level == "ALL":
            return True
        if lesson_level == teacher_level:
            return True
        chain = LEVEL_CHAIN.get(lesson_level, [])
        if teacher_level in chain:
            return True
        return {lesson_level, teacher_level} == {"PRESCHOOL", "ELEMENTARY"}


    candidates = []
    for t in teachers:
        if t.id == sub.absent_teacher_id or t.status != "ACTIVE":
            continue
        if not FreePeriodEngine.is_free(t, lesson.day, lesson.start_time, lesson.end_time):
            continue

        teacher_level = getattr(t, "school_level", "ALL") or "ALL"
        teacher_subjects = {s.lower() for s in (t.subjects or [])}
        # Fall back to actual lessons if subjects field not yet populated
        if not teacher_subjects:
            teacher_subjects = {l.subject.lower() for l in (t.lessons or [])}
        # Refine level from lessons if teacher is set to ALL but really teaches one level
        if teacher_level == "ALL" and t.lessons:
            lesson_levels = {l.school_level for l in t.lessons if l.school_level and l.school_level != "ALL"}
            if len(lesson_levels) == 1:
                teacher_level = lesson_levels.pop()
        subject_match = bool(lesson_subjects & teacher_subjects)
        same_level = level_matches(teacher_level)
        load_pct = round((len(t.duties or []) / (t.max_duties or 16)) * 100, 1)

        exact_level = (lesson_level == "ALL" or teacher_level == "ALL" or teacher_level == lesson_level)
        if subject_match and exact_level:
            tier, tier_label = 0, "Same subject & level"
        elif subject_match and same_level:
            tier, tier_label = 1, "Same subject, adj. level"
        elif exact_level:
            tier, tier_label = 1, "Same level, available"
        elif same_level:
            tier, tier_label = 2, "Adjacent level"
        else:
            tier, tier_label = 3, "Available"

        display_subjects = t.subjects or []
        if not display_subjects:
            display_subjects = sorted({l.subject for l in (t.lessons or [])})
        candidates.append({
            "teacher": {
                "id": t.id, "name": t.name, "initials": t.initials,
                "department": t.department,
                "subjects": display_subjects,
                "school_level": teacher_level,
            },
            "load_pct": load_pct,
            "score": round(100 - load_pct, 1),
            "tier": tier,
            "tier_label": tier_label,
            "subject_match": subject_match,
            "level_match": same_level,
        })

    candidates.sort(key=lambda c: (c["tier"], c["load_pct"]))
    return {"suggestions": candidates[:8]}


# ─── Whole-day substitution plan ─────────────────────────────────────────────

@router.get("/suggest")
def suggest_whole_day(
    teacher_id: str = Query(...),
    day: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a whole-day coverage plan for an absent teacher."""
    day_norm = normalize_day(day)
    sid = current_user.school_id

    absent = db.query(Teacher).options(
        joinedload(Teacher.lessons), joinedload(Teacher.duties),
    ).filter(
        Teacher.school_id == sid,
        Teacher.id == teacher_id,
    ).first()
    if not absent:
        raise HTTPException(status_code=404, detail="Teacher not found")

    lessons = [l for l in (absent.lessons or []) if normalize_day(l.day) == day_norm]
    lessons.sort(key=lambda l: l.start_time)

    candidate_pool = db.query(Teacher).options(
        joinedload(Teacher.lessons), joinedload(Teacher.duties),
    ).filter(
        Teacher.school_id == sid,
        Teacher.status == "ACTIVE",
    ).all()

    availability = Availability(day=day_norm)
    for t in candidate_pool:
        availability.add_lessons(t)
        availability.add_duties(t)

    # Existing substitutions this school. A substitute already booked
    # elsewhere at this time can't take a new one — but we only care
    # about bookings inside our tenant.
    active_subs = db.query(Substitution).options(
        joinedload(Substitution.lesson), joinedload(Substitution.duty),
    ).filter(
        Substitution.school_id == sid,
        Substitution.substitute_id.isnot(None),
        Substitution.status.in_(["PENDING", "ACCEPTED"]),
    ).all()
    for s in active_subs:
        if s.lesson:
            availability.add_existing_substitution(
                s.substitute_id, s.lesson.day, s.lesson.start_time, s.lesson.end_time,
            )
        elif s.duty:
            availability.add_existing_substitution(
                s.substitute_id, s.duty.day, s.duty.start_time, s.duty.end_time,
            )

    # Lessons in this day that already have a sub request.
    lesson_ids = [l.id for l in lessons]
    existing_by_lesson = {}
    if lesson_ids:
        for s in db.query(Substitution).filter(
            Substitution.school_id == sid,
            Substitution.lesson_id.in_(lesson_ids),
        ).all():
            existing_by_lesson[s.lesson_id] = s

    planner = DayPlanner(
        absent_teacher=absent,
        day=day_norm,
        candidate_pool=candidate_pool,
        availability=availability,
    )
    return planner.build(lessons, existing_by_lesson)


# ─── Atomic whole-day assignment ─────────────────────────────────────────────

class _Assignment(BaseModel):
    lesson_id: str = Field(..., min_length=1)
    substitute_id: str = Field(..., min_length=1)


class _AssignDayRequest(BaseModel):
    absent_teacher_id: str = Field(..., min_length=1)
    day: str = Field(..., min_length=3)
    assignments: list[_Assignment] = Field(..., min_length=1)


@router.post("/assign-day")
def assign_day(
    body: _AssignDayRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Commit a whole-day plan atomically.

    All assignments succeed together or the transaction rolls back. A
    substitute cannot be double-booked either against their own schedule
    or against another assignment within this same request.
    """
    day_norm = normalize_day(body.day)
    sid = current_user.school_id

    absent = db.query(Teacher).filter(
        Teacher.school_id == sid,
        Teacher.id == body.absent_teacher_id,
    ).first()
    if not absent:
        raise HTTPException(status_code=404, detail="Absent teacher not found")

    lesson_ids = [a.lesson_id for a in body.assignments]
    substitute_ids = list({a.substitute_id for a in body.assignments})

    lessons_by_id = {
        l.id: l for l in db.query(Lesson).filter(
            Lesson.school_id == sid,
            Lesson.id.in_(lesson_ids),
        ).all()
    }
    if len(lessons_by_id) != len(set(lesson_ids)):
        missing = set(lesson_ids) - set(lessons_by_id)
        raise HTTPException(
            status_code=400,
            detail=f"Lessons not found: {sorted(missing)}",
        )
    for l in lessons_by_id.values():
        if l.teacher_id != absent.id or normalize_day(l.day) != day_norm:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Lesson {l.id} does not belong to teacher {absent.id} on {day_norm}"
                ),
            )

    substitutes_by_id = {
        t.id: t for t in db.query(Teacher).options(
            joinedload(Teacher.lessons), joinedload(Teacher.duties),
        ).filter(
            Teacher.school_id == sid,
            Teacher.id.in_(substitute_ids),
            Teacher.status == "ACTIVE",
        ).all()
    }
    missing_subs = set(substitute_ids) - set(substitutes_by_id)
    if missing_subs:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or inactive substitute(s): {sorted(missing_subs)}",
        )
    if absent.id in substitutes_by_id:
        raise HTTPException(
            status_code=400,
            detail="Absent teacher cannot be their own substitute",
        )

    availability = Availability(day=day_norm)
    for t in substitutes_by_id.values():
        availability.add_lessons(t)
        availability.add_duties(t)

    day_subs = db.query(Substitution).options(
        joinedload(Substitution.lesson), joinedload(Substitution.duty),
    ).filter(
        Substitution.school_id == sid,
        Substitution.substitute_id.in_(substitute_ids),
        Substitution.status.in_(["PENDING", "ACCEPTED"]),
    ).all()
    for s in day_subs:
        if s.lesson:
            availability.add_existing_substitution(
                s.substitute_id, s.lesson.day, s.lesson.start_time, s.lesson.end_time,
            )
        elif s.duty:
            availability.add_existing_substitution(
                s.substitute_id, s.duty.day, s.duty.start_time, s.duty.end_time,
            )

    already_requested = db.query(Substitution).filter(
        Substitution.school_id == sid,
        Substitution.lesson_id.in_(lesson_ids),
    ).all()
    if already_requested:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "existing_substitution",
                "lesson_ids": [s.lesson_id for s in already_requested],
            },
        )

    conflicts: list[dict] = []
    reservations: list[tuple[str, str, str, str]] = []

    for item in body.assignments:
        lesson = lessons_by_id[item.lesson_id]
        if not availability.is_free(item.substitute_id, lesson.start_time, lesson.end_time):
            conflicts.append({
                "lesson_id": item.lesson_id,
                "substitute_id": item.substitute_id,
                "reason": "not_free",
                "at": f"{lesson.start_time}-{lesson.end_time}",
            })
            continue
        availability.reserve(item.substitute_id, lesson.start_time, lesson.end_time)
        reservations.append((item.lesson_id, item.substitute_id, lesson.start_time, lesson.end_time))

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"reason": "conflicts", "conflicts": conflicts},
        )

    created: list[dict] = []
    try:
        now = datetime.now(timezone.utc)
        for lesson_id, substitute_id, _s, _e in reservations:
            sub = Substitution(
                id=cuid.cuid(),
                lesson_id=lesson_id,
                absent_teacher_id=absent.id,
                substitute_id=substitute_id,
                status="ACCEPTED",
                resolved_at=now,
                school_id=sid,
            )
            db.add(sub)
            created.append({
                "substitution_id": sub.id,
                "lesson_id": lesson_id,
                "substitute_id": substitute_id,
                "status": sub.status,
            })

        lesson_summary = ", ".join(
            f"{lessons_by_id[a.lesson_id].subject} {lessons_by_id[a.lesson_id].class_}"
            for a in body.assignments
        )
        write_audit_log(
            db, actor=current_user, action="ASSIGN_DAY",
            details=(
                f"Whole-day sub plan for {absent.name} on {day_norm}: "
                f"{len(created)} lessons ({lesson_summary})"
            ),
            target_school_id=sid,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to commit day plan")

    for lesson_id, substitute_id, s, e in reservations:
        sub_teacher = substitutes_by_id[substitute_id]
        lesson = lessons_by_id[lesson_id]
        background_tasks.add_task(
            NotificationService.send_substitution_request,
            sub_teacher.email,
            sub_teacher.name,
            f"{lesson.subject} {lesson.class_}",
            f"{s}-{e}",
        )

    return {"created": created, "total": len(created), "day": day_norm}
