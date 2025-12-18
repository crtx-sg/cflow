"""Audit logging service."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditService:
    """Service for logging audit events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: int,
        old_value: Any = None,
        new_value: Any = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log an audit event.

        Args:
            user_id: ID of user performing action
            action: Action type (e.g., PROPOSAL_CREATED, STATUS_CHANGED)
            resource_type: Type of resource (e.g., "proposal", "comment")
            resource_id: ID of the affected resource
            old_value: Previous value (will be JSON serialized)
            new_value: New value (will be JSON serialized)
            ip_address: Client IP address

        Returns:
            Created AuditLog entry
        """
        entry = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=json.dumps(old_value) if old_value is not None else None,
            new_value=json.dumps(new_value) if new_value is not None else None,
            ip_address=ip_address,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def log_proposal_created(
        self,
        user_id: int,
        proposal_id: int,
        proposal_name: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log proposal creation."""
        return await self.log(
            user_id=user_id,
            action="PROPOSAL_CREATED",
            resource_type="proposal",
            resource_id=proposal_id,
            new_value={"name": proposal_name},
            ip_address=ip_address,
        )

    async def log_status_changed(
        self,
        user_id: int,
        proposal_id: int,
        old_status: str,
        new_status: str,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log proposal status change."""
        return await self.log(
            user_id=user_id,
            action="STATUS_CHANGED",
            resource_type="proposal",
            resource_id=proposal_id,
            old_value={"status": old_status},
            new_value={"status": new_status},
            ip_address=ip_address,
        )

    async def log_content_modified(
        self,
        user_id: int,
        proposal_id: int,
        file_path: str,
        version: int,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log content modification."""
        return await self.log(
            user_id=user_id,
            action="CONTENT_MODIFIED",
            resource_type="proposal",
            resource_id=proposal_id,
            new_value={"file_path": file_path, "version": version},
            ip_address=ip_address,
        )

    async def log_comment_resolved(
        self,
        user_id: int,
        comment_id: int,
        proposal_id: int,
        status: str,
        response: str | None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log comment resolution."""
        return await self.log(
            user_id=user_id,
            action="COMMENT_RESOLVED",
            resource_type="comment",
            resource_id=comment_id,
            new_value={
                "proposal_id": proposal_id,
                "status": status,
                "response": response,
            },
            ip_address=ip_address,
        )
