from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select
import db
from models import ActivityLog
from logger import get_logger

log = get_logger("logs_router")
router = APIRouter(prefix="/logs", tags=["logs"])

LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "career_studio.log"

ACTION_LABELS = {
    "import":       "Resume Imported",
    "export":       "Profile Exported",
    "patch":        "Profile Updated",
    "delete":       "Profile Deleted",
    "analyze":      "AI Analysis Run",
    "cover_letter": "Cover Letter Generated",
    "roadmap":      "Career Plan Generated",
    "jobs_search":  "Job Search Performed",
    "settings":     "Settings Updated",
    "error":        "Error Occurred",
}

ACTION_SEVERITY = {
    "import":       "info",
    "export":       "success",
    "patch":        "info",
    "delete":       "warning",
    "analyze":      "info",
    "cover_letter": "success",
    "roadmap":      "success",
    "jobs_search":  "info",
    "settings":     "info",
    "error":        "error",
}


@router.get("")
def get_logs(limit: int = Query(default=200, le=1000), action: str | None = None, level: str | None = None):
    with Session(db.engine) as session:
        q = select(ActivityLog).order_by(ActivityLog.id.desc())
        if action:
            q = q.where(ActivityLog.action == action)
        if level:
            q = q.where(ActivityLog.level == level)
        q = q.limit(limit)
        logs = session.exec(q).all()
        return [
            {
                "id":         l.id,
                "action":     l.action,
                "label":      ACTION_LABELS.get(l.action, l.action.replace("_", " ").title()),
                "severity":   l.level or ACTION_SEVERITY.get(l.action, "info"),
                "detail":     l.detail,
                "profile_id": l.profile_id,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ]


@router.get("/stats")
def log_stats():
    """Return counts per action type."""
    with Session(db.engine) as session:
        rows = session.exec(select(ActivityLog)).all()
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.action] = counts.get(r.action, 0) + 1
        return {"total": len(rows), "by_action": counts}


@router.get("/download")
def download_log_file():
    """Download the raw rotating log file from disk."""
    if not LOG_FILE.exists():
        return {"error": "Log file not found"}
    return FileResponse(
        path=str(LOG_FILE),
        filename="career_studio.log",
        media_type="text/plain",
    )


@router.delete("")
def clear_logs():
    with Session(db.engine) as session:
        logs = session.exec(select(ActivityLog)).all()
        for l in logs:
            session.delete(l)
        session.commit()
        log.info("Activity log cleared (%d entries removed)", len(logs))
        return {"deleted": len(logs)}
