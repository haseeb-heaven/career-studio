from fastapi import APIRouter
from sqlmodel import Session, select
from db import engine
from models import ActivityLog

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("")
def get_logs(limit: int = 100):
    with Session(engine) as session:
        logs = session.exec(
            select(ActivityLog).order_by(ActivityLog.id.desc()).limit(limit)
        ).all()
        return [
            {
                "id": l.id,
                "action": l.action,
                "detail": l.detail,
                "profile_id": l.profile_id,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ]

@router.delete("")
def clear_logs():
    with Session(engine) as session:
        logs = session.exec(select(ActivityLog)).all()
        for l in logs:
            session.delete(l)
        session.commit()
        return {"deleted": len(logs)}
