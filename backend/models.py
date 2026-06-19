from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func
import json


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", ondelete="CASCADE", index=True)
    # contact
    full_name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List["ContactLink"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    # sections
    summary: str = ""
    skills: List["Skill"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    experience: List["Experience"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    projects: List["Project"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    education: List["Education"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    certifications: List["Certification"] = Relationship(
        back_populates="profile",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    # meta
    availability: str = ""
    compensation: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class ContactLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    label: str
    url: str
    profile: Optional[Profile] = Relationship(back_populates="links")


class Skill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    name: str
    category: str = ""
    years: float = 0.0
    profile: Optional[Profile] = Relationship(back_populates="skills")


class ExperienceBullet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    experience_id: int = Field(foreign_key="experience.id", ondelete="CASCADE", index=True)
    text: str
    experience: Optional["Experience"] = Relationship(back_populates="bullets")


class Experience(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    company: str
    role: str
    start: str
    end: str = ""
    location: str = ""
    bullets: List[ExperienceBullet] = Relationship(
        back_populates="experience",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True},
    )
    profile: Optional[Profile] = Relationship(back_populates="experience")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    name: str
    description: str = ""
    link: str = ""
    tech: str = "[]"  # JSON array stored as string
    profile: Optional[Profile] = Relationship(back_populates="projects")

    def get_tech(self) -> List[str]:
        return json.loads(self.tech)

    def set_tech(self, items: List[str]) -> None:
        self.tech = json.dumps(items)


class Education(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    institution: str
    degree: str = ""
    field: str = ""
    start: str = ""
    end: str = ""
    profile: Optional[Profile] = Relationship(back_populates="education")


class Certification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    name: str
    cert_id: str = Field(default="", index=True)
    issuer: str = ""
    date: str = ""
    profile: Optional[Profile] = Relationship(back_populates="certifications")


class Settings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", ondelete="CASCADE", unique=True, index=True)
    # External API
    ai_provider: str = Field(default="openai")   # openai | anthropic | openrouter
    ai_model: str = Field(default="gpt-4o-mini")
    api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    adzuna_app_id: str = Field(default="")
    adzuna_app_key: str = Field(default="")
    linkedin_api_key: str = Field(default="")
    indeed_api_key: str = Field(default="")
    glassdoor_api_key: str = Field(default="")
    findwork_api_key: str = Field(default="")
    jooble_api_key: str = Field(default="")
    reed_api_key: str = Field(default="")
    usajobs_api_key: str = Field(default="")
    # Local AI (Ollama)
    use_local_ai: bool = Field(default=False)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")
    # Task routing: use local for quick tasks, external for heavy ones
    local_for_simple: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: str                          # "import" | "export" | "patch" | "delete" | "analyze" | "cover_letter" | "roadmap"
    detail: str = Field(default="")
    profile_id: Optional[int] = Field(default=None, foreign_key="profile.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoverLetter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    job_title: str = Field(default="")
    company: str = Field(default="")
    content: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class CareerPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    content: str = Field(default="")
    plan_type: str = Field(default="roadmap")   # roadmap | growth | portfolio
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class JobMatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE", index=True)
    title: str
    company: str = Field(default="")
    location: str = Field(default="")
    url: str = Field(default="")
    description: str = Field(default="")
    source: str = Field(default="")      # adzuna | remotive | himalayas | etc
    match_score: float = Field(default=0.0)
    salary: Optional[str] = Field(default=None)
    is_deep_link: bool = Field(default=False)
    # Issue #7 — advanced filter / sort / gap fields
    date_posted: str = Field(default="")
    job_type: str = Field(default="")     # full-time | part-time | contract | remote | hybrid
    industry: str = Field(default="")
    salary_min: int = Field(default=0)
    salary_max: int = Field(default=0)
    is_remote: bool = Field(default=False)
    is_expired: bool = Field(default=False)
    match_breakdown: str = Field(default="")        # JSON: {"skills": 40, "years": 20, ...}
    matched_skills: str = Field(default="[]")       # JSON list
    missing_skills: str = Field(default="[]")       # JSON list
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedFilter(SQLModel, table=True):
    """User-saved filter preset (Issue #7)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", ondelete="CASCADE", index=True)
    profile_id: Optional[int] = Field(default=None, foreign_key="profile.id", ondelete="CASCADE", index=True)
    name: str
    filters: str = Field(default="{}")
    sort: str = Field(default="best_match")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
