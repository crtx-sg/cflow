"""Review comment model for proposal review workflow."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class CommentStatus(str, Enum):
    """Comment resolution status."""

    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ReviewCommentBase(SQLModel):
    """Base review comment fields."""

    file_path: str
    line_start: int | None = Field(default=None)
    line_end: int | None = Field(default=None)
    content: str


class ReviewComment(ReviewCommentBase, table=True):
    """Review comment database model."""

    __tablename__ = "review_comments"

    id: int | None = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="change_proposals.id", index=True)
    reviewer_id: int = Field(foreign_key="users.id", index=True)
    status: CommentStatus = Field(default=CommentStatus.OPEN)
    author_response: str | None = Field(default=None)
    selected_for_iteration: bool = Field(default=False)
    parent_id: int | None = Field(default=None, foreign_key="review_comments.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = Field(default=None)
    resolved_by: int | None = Field(default=None, foreign_key="users.id")

    # Relationships
    proposal: "ChangeProposal" = Relationship(back_populates="comments")


class ReviewCommentCreate(SQLModel):
    """Schema for creating a review comment."""

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    content: str
    parent_id: int | None = None


class ReviewCommentRead(ReviewCommentBase):
    """Schema for reading a review comment."""

    id: int
    proposal_id: int
    reviewer_id: int
    status: CommentStatus
    author_response: str | None
    selected_for_iteration: bool
    parent_id: int | None
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: int | None


class ReviewCommentUpdate(SQLModel):
    """Schema for updating a review comment."""

    content: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class CommentResolve(SQLModel):
    """Schema for resolving a comment."""

    status: CommentStatus
    author_response: str | None = None


class CommentSelect(SQLModel):
    """Schema for selecting/deselecting comment for iteration."""

    selected_for_iteration: bool


# Import for type hints
from app.models.proposal import ChangeProposal  # noqa: E402, F401

ReviewComment.model_rebuild()
