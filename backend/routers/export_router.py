import db
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlmodel import Session
from exporters import exporter_for
from models import Profile
from logger import get_logger
from services.activity import log_activity

logger = get_logger(__name__)

router = APIRouter(prefix="/profiles", tags=["export"])

SUPPORTED = ["json", "csv", "xml", "docx", "pdf", "latex", "tex", "html", "portfolio"]


@router.get("/{profile_id}/export/{fmt}")
def export_profile(profile_id: int, fmt: str):
    if fmt not in SUPPORTED:
        raise HTTPException(400, f"Unsupported format: {fmt}. Choose from {SUPPORTED}")
    with Session(db.engine) as session:
        p = session.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, f"Profile {profile_id} not found")
        # Eagerly load relationships so exporter sees them
        _ = list(p.skills or [])
        _ = list(p.experience or [])
        for e in (p.experience or []):
            _ = list(e.bullets or [])
        _ = list(p.projects or [])
        _ = list(p.education or [])
        _ = list(p.certifications or [])
        _ = list(p.links or [])

        logger.info(f"Exporting profile {profile_id} as {fmt}")
        log_activity("export", f"profile #{profile_id} → {fmt}", profile_id)

        exporter = exporter_for(fmt)
        data = exporter.export(p)
        return Response(
            content=data,
            media_type=exporter.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{exporter.filename(p)}"'},
        )
