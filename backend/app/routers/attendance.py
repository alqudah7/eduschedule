import cuid
from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.teacher import Teacher
from app.models.attendance import TeacherAttendance
from app.schemas.attendance import AttendanceMark, AttendanceRecord, TeacherAttendanceRow, AttendanceSummary

router = APIRouter()


@router.post("/teachers", response_model=AttendanceRecord)
def mark_teacher_attendance(
    data: AttendanceMark,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    teacher = db.query(Teacher).filter(Teacher.id == data.teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    existing = (
        db.query(TeacherAttendance)
        .filter(
            TeacherAttendance.teacher_id == data.teacher_id,
            TeacherAttendance.date == data.date,
        )
        .first()
    )

    if existing:
        existing.status = data.status
        existing.note = data.note
        record = existing
    else:
        record = TeacherAttendance(
            id=cuid.cuid(),
            teacher_id=data.teacher_id,
            date=data.date,
            status=data.status,
            note=data.note,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.get("/teachers", response_model=list[TeacherAttendanceRow])
def list_attendance_for_date(
    date: date_type = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    teachers = db.query(Teacher).filter(Teacher.status != "INACTIVE").all()

    attendance_map: dict[str, TeacherAttendance] = {}
    records = db.query(TeacherAttendance).filter(TeacherAttendance.date == date).all()
    for r in records:
        attendance_map[r.teacher_id] = r

    rows = []
    for t in teachers:
        rec = attendance_map.get(t.id)
        rows.append(
            TeacherAttendanceRow(
                teacher_id=t.id,
                name=t.name,
                initials=t.initials,
                department=t.department,
                subjects=t.subjects or [],
                attendance_id=rec.id if rec else None,
                status=rec.status if rec else None,
                note=rec.note if rec else None,
            )
        )
    return rows


@router.get("/teachers/{teacher_id}", response_model=list[AttendanceRecord])
def get_teacher_attendance_history(
    teacher_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    records = (
        db.query(TeacherAttendance)
        .filter(TeacherAttendance.teacher_id == teacher_id)
        .order_by(TeacherAttendance.date.desc())
        .all()
    )
    return records


@router.get("/summary", response_model=AttendanceSummary)
def attendance_summary(
    date: date_type = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total = db.query(Teacher).filter(Teacher.status != "INACTIVE").count()
    records = db.query(TeacherAttendance).filter(TeacherAttendance.date == date).all()

    present = sum(1 for r in records if r.status == "present")
    absent = sum(1 for r in records if r.status == "absent")
    late = sum(1 for r in records if r.status == "late")
    marked = present + absent + late

    return AttendanceSummary(
        date=date,
        total=total,
        present=present,
        absent=absent,
        late=late,
        unmarked=total - marked,
    )
