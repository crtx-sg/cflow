"""Project model for compliance project management."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class ComplianceStandard(str, Enum):
    """Supported compliance standards."""

    IEC_62304 = "IEC_62304"
    ISO_26262 = "ISO_26262"
    DO_178C = "DO_178C"
    CUSTOM = "CUSTOM"


class OpenSpecTool(str, Enum):
    """Supported OpenSpec AI tools."""

    CLAUDE = "claude"
    CURSOR = "cursor"
    GITHUB_COPILOT = "github-copilot"
    WINDSURF = "windsurf"
    CLINE = "cline"
    AMAZON_Q = "amazon-q"
    GEMINI = "gemini"
    OPENCODE = "opencode"
    QODER = "qoder"
    ROOCODE = "roocode"
    NONE = "none"


class ProjectBase(SQLModel):
    """Base project fields."""

    name: str = Field(index=True)
    local_path: str
    compliance_standard: ComplianceStandard
    openspec_tool: OpenSpecTool = Field(default=OpenSpecTool.NONE)


class Project(ProjectBase, table=True):
    """Project database model."""

    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    # Relationships
    proposals: list["ChangeProposal"] = Relationship(back_populates="project")


class ProjectCreate(SQLModel):
    """Schema for creating a project."""

    name: str
    local_path: str
    compliance_standard: ComplianceStandard
    openspec_tool: OpenSpecTool | None = None  # If None, read from .env in project dir


class ProjectRead(ProjectBase):
    """Schema for reading a project."""

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(SQLModel):
    """Schema for updating a project."""

    name: str | None = None


# Import for type hints (avoid circular import at runtime)
from app.models.proposal import ChangeProposal  # noqa: E402, F401

Project.model_rebuild()
