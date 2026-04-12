from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SubstitutionCreate(BaseModel):
    duty_id: str
    absent_teacher_id: str
    notes: Optional[str] = None


class SubstituteSuggestion(BaseModel):
    teacher: dict
    load_pct: float
    score: float


class SuggestionsResponse(BaseModel):
    suggestions: List[SubstituteSuggestion]


class SubstitutionResponse(BaseModel):
    id: str
    duty_id: str
    duty: Optional[dict] = None
    absent_teacher_id: str
    absent_teacher: Optional[dict] = None
    substitute_id: Optional[str] = None
    substitute: Optional[dict] = None
    status: str
    requested_at: datetime
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
