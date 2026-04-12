from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AlertResponse(BaseModel):
    id: str
    severity: str
    title: str
    message: str
    duty_id: Optional[str] = None
    duty: Optional[dict] = None
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertSummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    total: int = 0
