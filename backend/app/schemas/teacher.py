from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class TeacherCreate(BaseModel):
    name: str
    department: str
    email: EmailStr
    phone: Optional[str] = None
    status: str = "ACTIVE"
    max_duties: int = 16
    qualifications: List[str] = []
    subjects: List[str] = []
    school_level: str = "ALL"
    password: str = "Teacher@123"


class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    max_duties: Optional[int] = None
    qualifications: Optional[List[str]] = None
    subjects: Optional[List[str]] = None
    school_level: Optional[str] = None


class TeacherResponse(BaseModel):
    id: str
    name: str
    initials: str
    department: str
    email: str
    phone: Optional[str] = None
    status: str
    max_duties: int
    qualifications: List[str]
    subjects: List[str]
    school_level: str = "ALL"
    duty_count: int = 0
    workload_pct: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherListResponse(BaseModel):
    teachers: List[TeacherResponse]
    total: int
