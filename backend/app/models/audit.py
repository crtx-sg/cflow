"""Audit log model for compliance audit trail."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """Immutable audit log for compliance tracking."""

    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    action: str = Field(index=True)  # e.g., PROPOSAL_CREATED, STATUS_CHANGED
    resource_type: str  # e.g., "proposal", "comment", "project"
    resource_id: int
    old_value: str | None = Field(default=None)  # JSON string
    new_value: str | None = Field(default=None)  # JSON string
    ip_address: str | None = Field(default=None)


class AuditLogRead(SQLModel):
    """Schema for reading audit log entries."""

    id: int
    timestamp: datetime
    user_id: int
    action: str
    resource_type: str
    resource_id: int
    old_value: str | None
    new_value: str | None
    ip_address: str | None
