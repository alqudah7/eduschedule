from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date, datetime


class AttendanceMark(BaseModel):
    teacher_id: str
    date: date
    status: Literal["present", "absent", "late"]
    note: Optional[str] = None


class AttendanceRecord(BaseModel):
    id: str
    teacher_id: str
    date: date
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherAttendanceRow(BaseModel):
    teacher_id: str
    name: str
    initials: str
    department: str
    subjects: List[str]
    attendance_id: Optional[str] = None
    status: Optional[str] = None  # null means unmarked
    note: Optional[str] = None


class AttendanceSummary(BaseModel):
    date: date
    total: int
    present: int
    absent: int
    late: int
    unmarked: int
