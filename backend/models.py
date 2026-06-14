from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func
import json


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # contact
    full_name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List["ContactLink"] = Relationship(back_populates="profile")
    # sections
    summary: str = ""
    skills: List["Skill"] = Relationship(back_populates="profile")
    experience: List["Experience"] = Relationship(back_populates="profile")
    projects: List["Project"] = Relationship(back_populates="profile")
    education: List["Education"] = Relationship(back_populates="profile")
    certifications: List["Certification"] = Relationship(back_populates="profile")
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
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    label: str
    url: str
    profile: Optional[Profile] = Relationship(back_populates="links")


class Skill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    name: str
    category: str = ""
    years: float = 0.0
    profile: Optional[Profile] = Relationship(back_populates="skills")


class ExperienceBullet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    experience_id: int = Field(foreign_key="experience.id", ondelete="CASCADE")
    text: str
    experience: Optional["Experience"] = Relationship(back_populates="bullets")


class Experience(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    company: str
    role: str
    start: str
    end: str = ""
    location: str = ""
    bullets: List[ExperienceBullet] = Relationship(back_populates="experience")
    profile: Optional[Profile] = Relationship(back_populates="experience")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
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
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    institution: str
    degree: str = ""
    field: str = ""
    start: str = ""
    end: str = ""
    profile: Optional[Profile] = Relationship(back_populates="education")


class Certification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    name: str
    issuer: str = ""
    date: str = ""
    profile: Optional[Profile] = Relationship(back_populates="certifications")


class Settings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ai_provider: str = Field(default="openai")   # openai | anthropic | openrouter
    ai_model: str = Field(default="gpt-4o-mini")
    api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: str                          # "import" | "export" | "patch" | "delete" | "analyze" | "cover_letter" | "roadmap"
    detail: str = Field(default="")
    profile_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoverLetter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
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
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    content: str = Field(default="")
    plan_type: str = Field(default="roadmap")   # roadmap | growth | portfolio
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class JobMatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", ondelete="CASCADE")
    title: str
    company: str = Field(default="")
    location: str = Field(default="")
    url: str = Field(default="")
    description: str = Field(default="")
    source: str = Field(default="")      # adzuna | remotive | github | etc
    match_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
