"""Proposal model for change proposal lifecycle."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class ProposalStatus(str, Enum):
    """Proposal status workflow states."""

    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"
    MERGED = "merged"


class ChangeProposalBase(SQLModel):
    """Base proposal fields."""

    name: str = Field(index=True)  # slug/kebab-case


class ChangeProposal(ChangeProposalBase, table=True):
    """Change proposal database model."""

    __tablename__ = "change_proposals"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    author_id: int = Field(foreign_key="users.id")
    status: ProposalStatus = Field(default=ProposalStatus.DRAFT)
    filesystem_path: str | None = Field(default=None)  # Set when READY
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: "Project" = Relationship(back_populates="proposals")
    contents: list["ProposalContent"] = Relationship(back_populates="proposal")
    comments: list["ReviewComment"] = Relationship(back_populates="proposal")


class ChangeProposalCreate(SQLModel):
    """Schema for creating a proposal."""

    name: str


class ChangeProposalRead(ChangeProposalBase):
    """Schema for reading a proposal."""

    id: int
    project_id: int
    author_id: int
    status: ProposalStatus
    filesystem_path: str | None
    created_at: datetime
    updated_at: datetime


# Import for type hints
from app.models.project import Project  # noqa: E402, F401
from app.models.content import ProposalContent  # noqa: E402, F401
from app.models.review import ReviewComment  # noqa: E402, F401

ChangeProposal.model_rebuild()
