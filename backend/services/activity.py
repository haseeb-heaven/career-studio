"""Activity log writer — records every significant action with rich detail."""
from datetime import datetime, timezone
from sqlmodel import Session
from models import ActivityLog
from db import engine
from logger import get_logger

log = get_logger("activity")

_LABELS = {
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


def log_activity(
    action: str,
    detail: str = "",
    profile_id: int | None = None,
    level: str = "info",
) -> None:
    label = _LABELS.get(action, action)
    msg = f"[{label}] {detail}" if detail else f"[{label}]"
    if profile_id is not None:
        msg += f" (profile #{profile_id})"

    getattr(log, level, log.info)(msg)

    try:
        with Session(engine) as s:
            s.add(ActivityLog(
                action=action,
                detail=detail,
                profile_id=profile_id,
                created_at=datetime.now(timezone.utc),
            ))
            s.commit()
    except Exception as exc:
        log.error("Failed to persist activity log: %s", exc)
