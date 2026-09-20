import csv, io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import Teacher, User
from app.models.duty import Duty
from app.models.substitution import Substitution
from app.models.alert import Alert, AuditLog
from app.models.attendance import TeacherAttendance

router = APIRouter()


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sid = current_user.school_id
    total_teachers = db.query(Teacher).filter(
        Teacher.school_id == sid, Teacher.status != "INACTIVE",
    ).count()
    active_today = db.query(Teacher).filter(
        Teacher.school_id == sid, Teacher.status == "ACTIVE",
    ).count()
    total_duties = db.query(Duty).filter(
        Duty.school_id == sid, Duty.status != "CANCELLED",
    ).count()
    issues_pending = db.query(Alert).filter(
        Alert.school_id == sid, Alert.resolved == False,
    ).count()
    duties_covered = db.query(Duty).filter(
        Duty.school_id == sid, Duty.status == "CONFIRMED",
    ).count()
    substitutions_made = db.query(Substitution).filter(
        Substitution.school_id == sid, Substitution.status == "ACCEPTED",
    ).count()
    conflicts_resolved = db.query(Duty).filter(
        Duty.school_id == sid, Duty.status == "CONFIRMED",
    ).count()
    return {
        "total_teachers": total_teachers,
        "active_today": active_today,
        "total_duties": total_duties,
        "issues_pending": issues_pending,
        "duties_covered": duties_covered,
        "substitutions_made": substitutions_made,
        "conflicts_resolved": conflicts_resolved,
    }


@router.get("/workload")
def workload(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import joinedload
    teachers = db.query(Teacher).filter(
        Teacher.school_id == current_user.school_id,
        Teacher.status != "INACTIVE",
    ).options(
        joinedload(Teacher.duties),
        joinedload(Teacher.attendances),
        joinedload(Teacher.substitutions_given),
    ).all()
    result = []
    for t in teachers:
        duty_count = len(t.duties) if t.duties else 0
        workload_pct = round((duty_count / (t.max_duties or 16)) * 100, 1)
        result.append({
            "teacher_id": t.id, "name": t.name, "department": t.department,
            "duty_count": duty_count, "max_duties": t.max_duties,
            "workload_pct": workload_pct,
            "absence_count": len(t.absences) if t.absences else 0,
            "sub_count": len(t.substitutions_given) if t.substitutions_given else 0,
        })
    return result


@router.get("/absences")
def absence_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Absence counts per week for the last 8 weeks.

    Reads teacher_attendance filtered by status='absent'. Absence table
    was consolidated into it in Alembic revision 21c773d1e916."""
    sid = current_user.school_id
    result = []
    now_date = datetime.now(timezone.utc).date()
    for i in range(8, 0, -1):
        week_start = now_date - timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)
        duty_count = db.query(Duty).filter(Duty.school_id == sid).count()
        absence_count = db.query(TeacherAttendance).filter(
            TeacherAttendance.school_id == sid,
            TeacherAttendance.status == "absent",
            TeacherAttendance.date >= week_start,
            TeacherAttendance.date < week_end,
        ).count()
        result.append({"week": f"Wk {9-i}", "duties": duty_count, "absences": absence_count})
    return result


@router.get("/audit-log")
def audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit
    total = db.query(AuditLog).filter(
        AuditLog.school_id == current_user.school_id,
    ).count()
    logs = db.query(AuditLog).filter(
        AuditLog.school_id == current_user.school_id,
    ).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "logs": [{"id": l.id, "action": l.action, "actor": l.actor, "details": l.details, "created_at": l.created_at} for l in logs],
        "total": total, "page": page, "limit": limit,
    }


@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duties = db.query(Duty).filter(Duty.school_id == current_user.school_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Type", "Day", "Start", "End", "Location", "Status", "Teacher ID"])
    for d in duties:
        writer.writerow([d.id, d.name, d.type, d.day, d.start_time, d.end_time, d.location, d.status, d.teacher_id or ""])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=duties.csv"},
    )
