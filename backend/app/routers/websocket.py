"""WebSocket endpoints for real-time updates."""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import JWTError, jwt
from sqlmodel import select

from app.core.config import get_settings
from app.core.database import get_session
from app.models import (
    ChangeProposal,
    Project,
    ProposalStatus,
    User,
    UserRole,
)
from app.services.content_versioning import ContentVersioningService
from app.services.iteration import IterationEngine
from app.services.openspec_client import openspec_client

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/ws")


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        # Map of proposal_id -> list of connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, proposal_id: int):
        await websocket.accept()
        if proposal_id not in self.active_connections:
            self.active_connections[proposal_id] = []
        self.active_connections[proposal_id].append(websocket)

    def disconnect(self, websocket: WebSocket, proposal_id: int):
        if proposal_id in self.active_connections:
            if websocket in self.active_connections[proposal_id]:
                self.active_connections[proposal_id].remove(websocket)
            if not self.active_connections[proposal_id]:
                del self.active_connections[proposal_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, proposal_id: int):
        if proposal_id in self.active_connections:
            for connection in self.active_connections[proposal_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass  # Connection may be closing


manager = ConnectionManager()


async def authenticate_websocket(
    websocket: WebSocket,
    token: str = Query(...),
) -> User | None:
    """Authenticate WebSocket connection using token query parameter."""
    async for session in get_session():
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            user_id: int = payload.get("sub")
            if user_id is None:
                return None

            result = await session.execute(
                select(User).where(User.id == int(user_id))
            )
            user = result.scalar_one_or_none()
            return user
        except JWTError:
            return None
        except Exception:
            return None


async def check_proposal_access(
    session,
    proposal_id: int,
    user: User,
) -> ChangeProposal | None:
    """Check if user has access to proposal."""
    result = await session.execute(
        select(ChangeProposal).where(ChangeProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        return None

    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        return None

    # Check access
    if user.role != UserRole.ADMIN:
        if project.owner_id != user.id and proposal.author_id != user.id:
            return None

    return proposal


@router.websocket("/proposals/{proposal_id}/validate")
async def validate_stream(
    websocket: WebSocket,
    proposal_id: int,
    token: str = Query(...),
):
    """WebSocket endpoint for streaming validation output."""
    user = await authenticate_websocket(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, proposal_id)

    async for session in get_session():
        try:
            proposal = await check_proposal_access(session, proposal_id, user)
            if not proposal:
                await manager.send_personal_message(
                    {"type": "error", "message": "Proposal not found or access denied"},
                    websocket
                )
                await websocket.close(code=4004)
                return

            # Get project path
            result = await session.execute(
                select(Project).where(Project.id == proposal.project_id)
            )
            project = result.scalar_one_or_none()

            # Get content and write to temp dir
            import tempfile
            from pathlib import Path

            versioning = ContentVersioningService(session)
            contents = await versioning.get_all_contents(proposal_id)

            if not contents:
                await manager.send_personal_message(
                    {"type": "error", "message": "No content to validate"},
                    websocket
                )
                await websocket.close(code=4000)
                return

            await manager.send_personal_message(
                {"type": "status", "message": "Starting validation..."},
                websocket
            )

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                changes_dir = temp_path / "openspec" / "changes" / proposal.name
                changes_dir.mkdir(parents=True, exist_ok=True)

                # Write files
                for content in contents:
                    file_path = changes_dir / content.file_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content.content)

                await manager.send_personal_message(
                    {"type": "output", "content": f"Validating {proposal.name}...\n"},
                    websocket
                )

                # Stream validation output
                async for line in openspec_client.validate_change_streaming(
                    temp_path, proposal.name, strict=True
                ):
                    await manager.send_personal_message(
                        {"type": "output", "content": line},
                        websocket
                    )

                # Get final result
                result = await openspec_client.validate_change(
                    temp_path, proposal.name, strict=True
                )

                await manager.send_personal_message(
                    {
                        "type": "complete",
                        "passed": result.passed,
                        "errors": result.errors,
                        "warnings": result.warnings,
                    },
                    websocket
                )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for proposal {proposal_id}")
        except Exception as e:
            logger.exception(f"Validation error for proposal {proposal_id}")
            await manager.send_personal_message(
                {"type": "error", "message": str(e)},
                websocket
            )
        finally:
            manager.disconnect(websocket, proposal_id)


@router.websocket("/proposals/{proposal_id}/iterate")
async def iterate_stream(
    websocket: WebSocket,
    proposal_id: int,
    token: str = Query(...),
):
    """WebSocket endpoint for streaming LLM iteration output."""
    user = await authenticate_websocket(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, proposal_id)

    async for session in get_session():
        try:
            proposal = await check_proposal_access(session, proposal_id, user)
            if not proposal:
                await manager.send_personal_message(
                    {"type": "error", "message": "Proposal not found or access denied"},
                    websocket
                )
                await websocket.close(code=4004)
                return

            # Only author can iterate
            if proposal.author_id != user.id and user.role != UserRole.ADMIN:
                await manager.send_personal_message(
                    {"type": "error", "message": "Only author can iterate"},
                    websocket
                )
                await websocket.close(code=4003)
                return

            if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REVIEW]:
                await manager.send_personal_message(
                    {"type": "error", "message": "Cannot iterate in current status"},
                    websocket
                )
                await websocket.close(code=4000)
                return

            # Wait for iteration request from client
            data = await websocket.receive_json()
            file_path = data.get("file_path")
            instructions = data.get("instructions", "")
            model = data.get("model")

            if not file_path:
                await manager.send_personal_message(
                    {"type": "error", "message": "file_path is required"},
                    websocket
                )
                continue

            await manager.send_personal_message(
                {"type": "status", "message": "Starting iteration..."},
                websocket
            )

            # Stream iteration
            engine = IterationEngine(session)
            async for chunk in engine.iterate_stream(
                proposal_id=proposal_id,
                file_path=file_path,
                user_id=user.id,
                instructions=instructions,
                model=model,
            ):
                if "error" in chunk:
                    await manager.send_personal_message(
                        {"type": "error", "message": chunk["error"]},
                        websocket
                    )
                elif "chunk" in chunk:
                    await manager.send_personal_message(
                        {"type": "chunk", "content": chunk["chunk"]},
                        websocket
                    )
                elif "complete" in chunk:
                    await manager.send_personal_message(
                        {
                            "type": "complete",
                            "version": chunk.get("version"),
                            "file_path": chunk.get("file_path"),
                        },
                        websocket
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for proposal {proposal_id}")
        except json.JSONDecodeError:
            await manager.send_personal_message(
                {"type": "error", "message": "Invalid JSON"},
                websocket
            )
        except Exception as e:
            logger.exception(f"Iteration error for proposal {proposal_id}")
            await manager.send_personal_message(
                {"type": "error", "message": str(e)},
                websocket
            )
        finally:
            manager.disconnect(websocket, proposal_id)


@router.websocket("/proposals/{proposal_id}/events")
async def proposal_events(
    websocket: WebSocket,
    proposal_id: int,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time proposal events (comments, status changes)."""
    user = await authenticate_websocket(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, proposal_id)

    async for session in get_session():
        try:
            proposal = await check_proposal_access(session, proposal_id, user)
            if not proposal:
                await manager.send_personal_message(
                    {"type": "error", "message": "Proposal not found or access denied"},
                    websocket
                )
                await websocket.close(code=4004)
                return

            await manager.send_personal_message(
                {"type": "connected", "proposal_id": proposal_id},
                websocket
            )

            # Keep connection alive and handle pings
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=30.0
                    )
                    if data.get("type") == "ping":
                        await manager.send_personal_message(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                            websocket
                        )
                except asyncio.TimeoutError:
                    # Send keepalive
                    await manager.send_personal_message(
                        {"type": "keepalive"},
                        websocket
                    )

        except WebSocketDisconnect:
            logger.info(f"Events WebSocket disconnected for proposal {proposal_id}")
        except Exception as e:
            logger.exception(f"Events error for proposal {proposal_id}")
        finally:
            manager.disconnect(websocket, proposal_id)


# Helper function to broadcast events to connected clients
async def broadcast_event(proposal_id: int, event_type: str, data: dict):
    """Broadcast an event to all connected clients for a proposal."""
    message = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    }
    await manager.broadcast(message, proposal_id)
