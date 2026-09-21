import cuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.alert import Alert, AuditLog
from app.models.teacher import User
from app.utils.audit import write_audit_log

router = APIRouter()


def _alert_to_dict(a: Alert) -> dict:
    result = {
        "id": a.id, "severity": a.severity, "title": a.title,
        "message": a.message, "duty_id": a.duty_id,
        "resolved": a.resolved, "created_at": a.created_at,
    }
    if a.duty:
        result["duty"] = {
            "id": a.duty.id, "name": a.duty.name, "type": a.duty.type,
            "day": a.duty.day, "start_time": a.duty.start_time, "end_time": a.duty.end_time,
        }
    return result


@router.get("/summary")
def alert_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = db.query(Alert).filter(
        Alert.school_id == current_user.school_id,
        Alert.resolved == False,
    ).all()
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for a in alerts:
        key = a.severity.lower()
        if key in counts:
            counts[key] += 1
    counts["total"] = sum(counts.values())
    return counts


@router.get("/")
def list_alerts(
    resolved: Optional[bool] = Query(False),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Alert).options(joinedload(Alert.duty)).filter(
        Alert.school_id == current_user.school_id,
    )
    if resolved is not None:
        q = q.filter(Alert.resolved == resolved)
    if severity:
        q = q.filter(Alert.severity == severity.upper())
    alerts = q.order_by(Alert.created_at.desc()).all()
    return {"alerts": [_alert_to_dict(a) for a in alerts], "total": len(alerts)}


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    alert = db.query(Alert).filter(
        Alert.school_id == current_user.school_id,
        Alert.id == alert_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    write_audit_log(db, actor=current_user, action="RESOLVE_ALERT",
                    details=f"Resolved alert: {alert.title}")
    db.commit()
    return {"message": "Alert resolved"}
