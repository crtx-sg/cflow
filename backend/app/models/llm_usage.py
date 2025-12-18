"""LLM usage tracking models."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class LLMUsage(SQLModel, table=True):
    """Track LLM API usage for cost monitoring and analytics."""

    __tablename__ = "llm_usage"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Request context
    user_id: int = Field(foreign_key="users.id", index=True)
    proposal_id: Optional[int] = Field(default=None, foreign_key="change_proposals.id", index=True)

    # Provider and model info
    provider: str = Field(index=True)
    model: str

    # Token usage
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)

    # Request metadata
    operation: str = Field(index=True)  # e.g., "iterate", "generate_section"
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = Field(default=None)


class LLMUsageCreate(SQLModel):
    """Schema for creating LLM usage records."""

    user_id: int
    proposal_id: Optional[int] = None
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    operation: str
    success: bool = True
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class LLMUsageSummary(SQLModel):
    """Summary statistics for LLM usage."""

    total_requests: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    success_rate: float
    providers: dict[str, int]  # provider -> request count
    operations: dict[str, int]  # operation -> request count
