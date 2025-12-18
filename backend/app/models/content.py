"""Content models for proposal file storage and versioning."""

from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class ProposalContentBase(SQLModel):
    """Base proposal content fields."""

    file_path: str  # e.g., "proposal.md", "specs/auth/spec.md"
    content: str = Field(default="")


class ProposalContent(ProposalContentBase, table=True):
    """Current proposal content stored in database."""

    __tablename__ = "proposal_contents"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="change_proposals.id", index=True)
    version: int = Field(default=1)
    updated_by: int = Field(foreign_key="users.id")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    proposal: "ChangeProposal" = Relationship(back_populates="contents")


class ContentVersion(SQLModel, table=True):
    """Version history for proposal content."""

    __tablename__ = "content_versions"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="change_proposals.id", index=True)
    file_path: str
    content: str
    version: int
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: str | None = Field(default=None)


class ProposalContentRead(ProposalContentBase):
    """Schema for reading proposal content."""

    id: int
    proposal_id: int
    version: int
    updated_by: int
    updated_at: datetime


class ProposalContentUpdate(SQLModel):
    """Schema for updating proposal content."""

    content: str
    change_reason: str | None = None


class ContentVersionRead(SQLModel):
    """Schema for reading content version history."""

    id: int
    proposal_id: int
    file_path: str
    version: int
    created_by: int
    created_at: datetime
    change_reason: str | None


# Import for type hints
from app.models.proposal import ChangeProposal  # noqa: E402, F401

ProposalContent.model_rebuild()
