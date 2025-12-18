"""Audit log endpoints."""

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.core.deps import CurrentUser, DbSession
from app.models import (
    AuditLog,
    AuditLogRead,
    UserRole,
)

router = APIRouter(prefix="/audit")


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    current_user: CurrentUser,
    session: DbSession,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[AuditLog]:
    """List audit logs with filters (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = select(AuditLog)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(AuditLog.resource_id == resource_id)
    if since is not None:
        query = query.where(AuditLog.timestamp >= since)
    if until is not None:
        query = query.where(AuditLog.timestamp <= until)

    query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{audit_id}", response_model=AuditLogRead)
async def get_audit_log(
    audit_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> AuditLog:
    """Get a specific audit log entry (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await session.execute(
        select(AuditLog).where(AuditLog.id == audit_id)
    )
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return audit


@router.get("/resource/{resource_type}/{resource_id}", response_model=list[AuditLogRead])
async def get_resource_audit(
    resource_type: str,
    resource_id: int,
    current_user: CurrentUser,
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[AuditLog]:
    """Get audit log for a specific resource.

    Non-admin users can only view audit logs for resources they own/authored.
    """
    query = select(AuditLog).where(
        AuditLog.resource_type == resource_type,
        AuditLog.resource_id == resource_id,
    )

    # Non-admin users can only see their own actions
    if current_user.role != UserRole.ADMIN:
        query = query.where(AuditLog.user_id == current_user.id)

    query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/actions", response_model=list[str])
async def list_action_types(
    current_user: CurrentUser,
    session: DbSession,
) -> list[str]:
    """List all distinct action types in the audit log."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await session.execute(
        select(AuditLog.action).distinct()
    )
    return [row[0] for row in result.all()]


@router.get("/export")
async def export_audit_logs(
    current_user: CurrentUser,
    session: DbSession,
    format: Literal["csv", "json"] = "csv",
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(10000, ge=1, le=100000),
):
    """Export audit logs (Admin only).

    Returns CSV or JSON file download.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Build query
    query = select(AuditLog)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)
    if since is not None:
        query = query.where(AuditLog.timestamp >= since)
    if until is not None:
        query = query.where(AuditLog.timestamp <= until)

    query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

    result = await session.execute(query)
    logs = list(result.scalars().all())

    if format == "csv":
        return _export_csv(logs)
    else:
        return _export_json(logs)


def _export_csv(logs: list[AuditLog]) -> StreamingResponse:
    """Export logs as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "id",
        "timestamp",
        "user_id",
        "action",
        "resource_type",
        "resource_id",
        "old_value",
        "new_value",
        "ip_address",
    ])

    # Data
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat(),
            log.user_id,
            log.action,
            log.resource_type,
            log.resource_id,
            log.old_value,
            log.new_value,
            log.ip_address,
        ])

    output.seek(0)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_export_{timestamp}.csv"
        },
    )


def _export_json(logs: list[AuditLog]) -> StreamingResponse:
    """Export logs as JSON."""
    data = []
    for log in logs:
        data.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "old_value": json.loads(log.old_value) if log.old_value else None,
            "new_value": json.loads(log.new_value) if log.new_value else None,
            "ip_address": log.ip_address,
        })

    output = json.dumps(data, indent=2)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=audit_export_{timestamp}.json"
        },
    )


@router.get("/summary", response_model=dict)
async def get_audit_summary(
    current_user: CurrentUser,
    session: DbSession,
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get audit summary statistics (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    since = datetime.utcnow() - timedelta(days=days)

    # Get all logs in the period
    result = await session.execute(
        select(AuditLog).where(AuditLog.timestamp >= since)
    )
    logs = list(result.scalars().all())

    # Aggregate by action
    by_action: dict[str, int] = {}
    for log in logs:
        by_action[log.action] = by_action.get(log.action, 0) + 1

    # Aggregate by resource type
    by_resource: dict[str, int] = {}
    for log in logs:
        by_resource[log.resource_type] = by_resource.get(log.resource_type, 0) + 1

    # Aggregate by user
    by_user: dict[int, int] = {}
    for log in logs:
        by_user[log.user_id] = by_user.get(log.user_id, 0) + 1

    # Top 10 users by activity
    top_users = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "period_days": days,
        "total_events": len(logs),
        "by_action": by_action,
        "by_resource_type": by_resource,
        "top_users": [{"user_id": u, "count": c} for u, c in top_users],
    }
