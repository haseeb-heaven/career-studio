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
