"""Analysis endpoints: resume score, AI suggestions, cover letter, career roadmap."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from db import engine
from models import Profile, CoverLetter, CareerPlan, User
from services import activity
from services.ai_service import complete_simple, complete_complex, profile_text_summary
from logger import get_logger
from routers.auth_utils import get_current_user
from routers.profile_router import _check_ownership

logger = get_logger(__name__)
router = APIRouter(prefix="/profiles", tags=["analysis"])


def _get_profile(pid: int, session: Session) -> Profile:
    p = session.get(Profile, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.refresh(p)
    return p


# ---------- /analyze ----------

@router.post("/{profile_id}/analyze")
def analyze(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    system = (
        "You are a senior technical recruiter and career coach. "
        "Analyze the resume and return a JSON object with these keys:\n"
        '  "score": integer 0-100,\n'
        '  "strengths": list of 3-5 short strings,\n'
        '  "weaknesses": list of 3-5 short strings,\n'
        '  "suggestions": list of 5-7 specific, actionable improvement suggestions,\n'
        '  "ats_keywords": list of 10 ATS keywords missing from the resume.\n'
        "Return ONLY valid JSON. No prose."
    )
    user_msg = f"Resume:\n{resume_text}"

    try:
        raw = complete_simple(system, user_msg)
        import json
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
    except Exception as e:
        logger.error("AI analysis failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    activity.log_activity("analyze", f"score={result.get('score')}", profile_id)
    return result


# ---------- /score ----------

@router.get("/{profile_id}/score")
def score(profile_id: int, user: User = Depends(get_current_user)):
    """Quick score-only endpoint (same AI call, cheaper to display)."""
    return analyze(profile_id, user)


# ---------- /cover-letter ----------

class CoverLetterRequest(BaseModel):
    job_title: str
    company: str
    extra_notes: str = ""


@router.post("/{profile_id}/cover-letter")
def generate_cover_letter(
    profile_id: int,
    body: CoverLetterRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    system = (
        "You are an expert career coach. Write a professional, enthusiastic, "
        "and personalized cover letter in the first person. "
        "The letter should be 3-4 paragraphs: opening hook, skills/experience match, "
        "why this company, call to action. Do not add placeholders. "
        "Return ONLY the cover letter text, no subject line or date header."
    )
    user_msg = (
        f"Job Title: {body.job_title}\n"
        f"Company: {body.company}\n"
        f"Extra notes: {body.extra_notes}\n\n"
        f"Resume:\n{resume_text}"
    )

    try:
        content = complete_complex(system, user_msg)
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    with Session(engine) as s:
        cl = CoverLetter(
            profile_id=profile_id,
            job_title=body.job_title,
            company=body.company,
            content=content,
        )
        s.add(cl)
        s.commit()
        s.refresh(cl)
        activity.log_activity("cover_letter", f"{body.job_title} @ {body.company}", profile_id)
        return {"id": cl.id, "content": cl.content, "job_title": cl.job_title, "company": cl.company}


@router.get("/{profile_id}/cover-letters")
def list_cover_letters(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        rows = s.exec(select(CoverLetter).where(CoverLetter.profile_id == profile_id)).all()
        return [
            {
                "id": r.id, "job_title": r.job_title, "company": r.company,
                "content": r.content, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@router.delete("/{profile_id}/cover-letters/{cl_id}")
def delete_cover_letter(
    profile_id: int,
    cl_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        cl = s.get(CoverLetter, cl_id)
        if not cl or cl.profile_id != profile_id:
            raise HTTPException(status_code=404)
        s.delete(cl)
        s.commit()
        return {"ok": True}


# ---------- /roadmap ----------

class RoadmapRequest(BaseModel):
    plan_type: str = "roadmap"   # roadmap | growth | portfolio
    target_role: str = ""
    years_horizon: int = 3


@router.post("/{profile_id}/roadmap")
def generate_roadmap(
    profile_id: int,
    body: RoadmapRequest,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        resume_text = profile_text_summary(p)

    plan_prompts = {
        "roadmap": (
            "Create a detailed {years}-year career roadmap targeting the role '{role}'. "
            "You must return a single JSON object with this exact structure:\n"
            "{{\n"
            "  \"title\": \"Career Roadmap to {role}\",\n"
            "  \"overview\": \"A 2-3 sentence overview of the starting point vs. target role.\",\n"
            "  \"timeline\": [\n"
            "    {{\n"
            "      \"period\": \"Year 1\",\n"
            "      \"milestones\": [\"milestone 1\", \"milestone 2\"],\n"
            "      \"skills\": [\"skill 1\", \"skill 2\"],\n"
            "      \"certifications\": [\"cert 1\"],\n"
            "      \"actions\": [\"networking action 1\", \"target company list\"]\n"
            "    }}\n"
            "  ],\n"
            "  \"projects\": [\n"
            "    {{\n"
            "      \"name\": \"Portfolio Project\",\n"
            "      \"description\": \"Description of what to build to show capability.\",\n"
            "      \"tech_stack\": [\"tech 1\", \"tech 2\"],\n"
            "      \"github_strategy\": \"How to structure/document the repo.\"\n"
            "    }}\n"
            "  ],\n"
            "  \"learning_resources\": [\n"
            "    {{\n"
            "      \"title\": \"Specific Course or Topic\",\n"
            "      \"platform\": \"YouTube / Coursera / Udemy / edX / Books\",\n"
            "      \"url\": \"https://www.youtube.com/results?search_query=advanced+typescript\",\n"
            "      \"description\": \"Why this resource is essential.\"\n"
            "    }}\n"
            "  ],\n"
            "  \"additional_strategy\": \"Salary progression expectations over {years} years.\"\n"
            "}}\n"
            "IMPORTANT: Return ONLY this JSON. Do not write any introduction or conclusion."
        ),
        "growth": (
            "Create a detailed {years}-year personal growth plan targeting the role '{role}'. "
            "Return a JSON object with keys: title, overview, timeline, projects, learning_resources, additional_strategy. "
            "IMPORTANT: Return ONLY this JSON."
        ),
        "portfolio": (
            "Create a detailed {years}-year portfolio strategy targeting the role '{role}'. "
            "Return a JSON object with keys: title, overview, timeline, projects, learning_resources, additional_strategy. "
            "IMPORTANT: Return ONLY this JSON."
        ),
    }

    template = plan_prompts.get(body.plan_type, plan_prompts["roadmap"])
    prompt_suffix = template.format(years=body.years_horizon, role=body.target_role or "senior engineer")

    system = "You are an expert career coach with 20 years of tech experience. Return ONLY valid JSON."
    user_msg = f"Resume:\n{resume_text}\n\nTask: {prompt_suffix}"

    try:
        content = complete_complex(system, user_msg)
        content_stripped = content.strip()
        if content_stripped.startswith("```"):
            parts = content_stripped.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    import json
                    json.loads(part)
                    content = part
                    break
                except Exception:
                    pass
    except Exception as e:
        logger.error("Roadmap generation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    with Session(engine) as s:
        plan = CareerPlan(
            profile_id=profile_id,
            content=content,
            plan_type=body.plan_type,
        )
        s.add(plan)
        s.commit()
        s.refresh(plan)
        activity.log_activity("roadmap", f"type={body.plan_type}", profile_id)
        return {"id": plan.id, "content": plan.content, "plan_type": plan.plan_type}


@router.get("/{profile_id}/roadmaps")
def list_roadmaps(profile_id: int, user: User = Depends(get_current_user)):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        rows = s.exec(select(CareerPlan).where(CareerPlan.profile_id == profile_id)).all()
        return [
            {
                "id": r.id, "plan_type": r.plan_type,
                "content": r.content, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


@router.delete("/{profile_id}/roadmaps/{plan_id}")
def delete_roadmap(
    profile_id: int,
    plan_id: int,
    user: User = Depends(get_current_user),
):
    with Session(engine) as s:
        p = _get_profile(profile_id, s)
        _check_ownership(p, user)
        plan = s.get(CareerPlan, plan_id)
        if not plan or plan.profile_id != profile_id:
            raise HTTPException(status_code=404)
        s.delete(plan)
        s.commit()
        return {"ok": True}
