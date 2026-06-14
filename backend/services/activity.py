from sqlmodel import Session
from models import ActivityLog
from db import engine


def log_activity(action: str, detail: str = "", profile_id: int | None = None) -> None:
    with Session(engine) as s:
        s.add(ActivityLog(action=action, detail=detail, profile_id=profile_id))
        s.commit()
