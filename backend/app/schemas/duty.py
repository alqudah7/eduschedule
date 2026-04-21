from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.schemas.teacher import TeacherResponse


class DutyCreate(BaseModel):
    name: str
    type: str
    day: str
    start_time: str
    end_time: str
    location: str
    teacher_id: Optional[str] = None
    duty_category: str = "SUPERVISION"
    notes: Optional[str] = None


class DutyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    teacher_id: Optional[str] = None
    status: Optional[str] = None
    duty_category: Optional[str] = None
    notes: Optional[str] = None


class DutyResponse(BaseModel):
    id: str
    name: str
    type: str
    day: str
    start_time: str
    end_time: str
    location: str
    teacher_id: Optional[str] = None
    teacher: Optional[dict] = None
    status: str
    duty_category: str = "SUPERVISION"
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DutyListResponse(BaseModel):
    duties: List[DutyResponse]
    total: int
