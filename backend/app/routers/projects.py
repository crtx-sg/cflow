"""Project management endpoints."""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

logger = logging.getLogger(__name__)

from app.core.deps import CurrentUser, DbSession
from app.models import (
    ChangeProposal,
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    OpenSpecTool,
    ProposalStatus,
    UserRole,
)
from app.services.audit import AuditService
from app.services.content_versioning import ContentVersioningService
from app.services.filesystem import validate_project_directory, PathValidationError
from app.services.openspec_client import openspec_client
from app.services.proposal_generator import ProposalGeneratorService


# Request/Response models for AI generation
class AnalyzeProposalsRequest(BaseModel):
    """Request for analyzing context into proposals."""
    context: str = Field(..., min_length=100, description="Detailed system context")


class ProposalSuggestionResponse(BaseModel):
    """A suggested proposal."""
    name: str
    description: str
    category: str


class AnalyzeProposalsResponse(BaseModel):
    """Response from context analysis."""
    suggestions: list[ProposalSuggestionResponse]
    analysis_summary: str
    tokens_used: int | None = None


class ProposalToCreate(BaseModel):
    """A proposal to create."""
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$", min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)


class CreateProposalsRequest(BaseModel):
    """Request for batch creating proposals."""
    proposals: list[ProposalToCreate] = Field(..., min_length=1, max_length=20)
    original_context: str | None = None


class CreatedProposalResponse(BaseModel):
    """A successfully created proposal."""
    id: int
    name: str
    status: str
    files_created: list[str]


class FailedProposalResponse(BaseModel):
    """A proposal that failed to create."""
    name: str
    error: str


class CreateProposalsResponse(BaseModel):
    """Response from batch proposal creation."""
    created: list[CreatedProposalResponse]
    failed: list[FailedProposalResponse]
    total_tokens_used: int


def _read_tool_from_env(local_path: str) -> OpenSpecTool | None:
    """Read OPENSPEC_TOOL from project's .env file."""
    env_file = Path(local_path) / ".env"
    if not env_file.exists():
        return None

    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENSPEC_TOOL="):
                    tool_value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    try:
                        return OpenSpecTool(tool_value)
                    except ValueError:
                        return None
    except Exception:
        return None

    return None

router = APIRouter(prefix="/projects")


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> Project:
    """Create a new project and initialize OpenSpec."""
    # Validate directory exists
    try:
        validate_project_directory(project_data.local_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for duplicate name
    result = await session.execute(
        select(Project).where(
            Project.name == project_data.name,
            Project.is_deleted == False,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project name already exists")

    # Determine OpenSpec tool: from request, .env file, or default to 'none'
    openspec_tool = project_data.openspec_tool
    if openspec_tool is None:
        openspec_tool = _read_tool_from_env(project_data.local_path)
    if openspec_tool is None:
        openspec_tool = OpenSpecTool.NONE

    # Initialize OpenSpec in directory with the configured tool
    cli_result = await openspec_client.init_project(
        project_data.local_path,
        openspec_tool.value,
    )
    if not cli_result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize OpenSpec: {cli_result.stderr}",
        )

    # Create project record
    project = Project(
        name=project_data.name,
        local_path=project_data.local_path,
        compliance_standard=project_data.compliance_standard,
        openspec_tool=openspec_tool,
        owner_id=current_user.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    # Audit log
    audit = AuditService(session)
    await audit.log(
        user_id=current_user.id,
        action="PROJECT_CREATED",
        resource_type="project",
        resource_id=project.id,
        new_value={
            "name": project.name,
            "standard": project.compliance_standard.value,
            "openspec_tool": project.openspec_tool.value,
        },
    )

    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    current_user: CurrentUser,
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Project]:
    """List projects accessible to current user."""
    query = select(Project).where(Project.is_deleted == False)

    # Non-admin users only see their own projects
    if current_user.role != UserRole.ADMIN:
        query = query.where(Project.owner_id == current_user.id)

    query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> Project:
    """Get project details."""
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> Project:
    """Update project (name only, standard is immutable)."""
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access (owner or admin)
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    old_name = project.name
    if project_data.name is not None:
        project.name = project_data.name
    project.updated_at = datetime.utcnow()

    session.add(project)
    await session.commit()
    await session.refresh(project)

    # Audit log
    audit = AuditService(session)
    await audit.log(
        user_id=current_user.id,
        action="PROJECT_UPDATED",
        resource_type="project",
        resource_id=project.id,
        old_value={"name": old_name},
        new_value={"name": project.name},
    )

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    """Soft delete a project (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_deleted = True
    project.updated_at = datetime.utcnow()
    session.add(project)
    await session.commit()

    # Audit log
    audit = AuditService(session)
    await audit.log(
        user_id=current_user.id,
        action="PROJECT_DELETED",
        resource_type="project",
        resource_id=project.id,
    )


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get project statistics."""
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Count proposals by status
    status_counts = {}
    for status_value in ProposalStatus:
        result = await session.execute(
            select(ChangeProposal).where(
                ChangeProposal.project_id == project_id,
                ChangeProposal.status == status_value,
            )
        )
        status_counts[status_value.value] = len(list(result.scalars().all()))

    return {
        "project_id": project_id,
        "proposal_counts": status_counts,
        "total_proposals": sum(status_counts.values()),
    }


# AI-assisted proposal generation endpoints

async def _get_project_with_access(
    project_id: int, session, current_user
) -> Project:
    """Get project and verify access."""
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


@router.post("/{project_id}/analyze-proposals", response_model=AnalyzeProposalsResponse)
async def analyze_proposals(
    project_id: int,
    request: AnalyzeProposalsRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> AnalyzeProposalsResponse:
    """Analyze detailed context and suggest proposals.

    Takes a detailed system description including problem, solution, users,
    authentication, data flow, components, and tech stack, then returns
    a list of suggested proposals with names and descriptions.
    """
    project = await _get_project_with_access(project_id, session, current_user)

    generator = ProposalGeneratorService(project.openspec_tool.value)
    result = await generator.analyze_context(
        context=request.context,
        compliance_standard=project.compliance_standard.value,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return AnalyzeProposalsResponse(
        suggestions=[
            ProposalSuggestionResponse(
                name=s.name,
                description=s.description,
                category=s.category,
            )
            for s in result.suggestions
        ],
        analysis_summary=result.analysis_summary,
        tokens_used=result.tokens_used,
    )


@router.post("/{project_id}/create-proposals", response_model=CreateProposalsResponse)
async def create_proposals(
    project_id: int,
    request: CreateProposalsRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> CreateProposalsResponse:
    """Create multiple proposals with AI-generated content.

    For each proposal in the request:
    1. Validates name uniqueness and kebab-case format
    2. Creates proposal record in database
    3. Generates proposal.md, tasks.md, and spec.md content
    4. Saves content via versioning service

    Continues processing remaining proposals if some fail.
    """
    project = await _get_project_with_access(project_id, session, current_user)

    generator = ProposalGeneratorService(project.openspec_tool.value)
    versioning = ContentVersioningService(session)
    audit = AuditService(session)

    created: list[CreatedProposalResponse] = []
    failed: list[FailedProposalResponse] = []
    total_tokens = 0

    for idx, proposal_to_create in enumerate(request.proposals):
        logger.info(f"Processing proposal {idx + 1}/{len(request.proposals)}: {proposal_to_create.name}")
        try:
            # Add a small delay between proposals to avoid overwhelming the LLM
            if idx > 0:
                await asyncio.sleep(1.0)

            # Validate name format
            if not re.match(r'^[a-z][a-z0-9-]*[a-z0-9]$', proposal_to_create.name):
                raise ValueError("Name must be kebab-case (e.g., add-user-authentication)")

            # Check for duplicate name
            result = await session.execute(
                select(ChangeProposal).where(
                    ChangeProposal.project_id == project_id,
                    ChangeProposal.name == proposal_to_create.name,
                )
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Proposal '{proposal_to_create.name}' already exists")

            # Generate content
            logger.info(f"Generating content for proposal: {proposal_to_create.name}")
            gen_result = await generator.generate_proposal_content(
                name=proposal_to_create.name,
                description=proposal_to_create.description,
                compliance_standard=project.compliance_standard.value,
                original_context=request.original_context,
            )

            if not gen_result.success:
                raise ValueError(gen_result.error or "Content generation failed")

            if gen_result.tokens_used:
                total_tokens += gen_result.tokens_used

            # Create proposal record
            proposal = ChangeProposal(
                name=proposal_to_create.name,
                project_id=project_id,
                author_id=current_user.id,
                status=ProposalStatus.DRAFT,
            )
            session.add(proposal)
            await session.commit()
            await session.refresh(proposal)

            # Save generated content
            files_created = []

            await versioning.save_content(
                proposal_id=proposal.id,
                file_path="proposal.md",
                content=gen_result.content.proposal_md,
                user_id=current_user.id,
                change_reason="Generated via AI from project context",
            )
            files_created.append("proposal.md")

            await versioning.save_content(
                proposal_id=proposal.id,
                file_path="tasks.md",
                content=gen_result.content.tasks_md,
                user_id=current_user.id,
                change_reason="Generated via AI from project context",
            )
            files_created.append("tasks.md")

            # Save spec delta
            # Create spec directory structure: specs/{capability}/spec.md
            capability_name = proposal_to_create.name.replace("-", "_")
            spec_path = f"specs/{capability_name}/spec.md"
            await versioning.save_content(
                proposal_id=proposal.id,
                file_path=spec_path,
                content=gen_result.content.spec_md,
                user_id=current_user.id,
                change_reason="Generated via AI from project context",
            )
            files_created.append(spec_path)

            # Audit log
            await audit.log(
                user_id=current_user.id,
                action="PROPOSAL_CREATED_VIA_AI",
                resource_type="proposal",
                resource_id=proposal.id,
                new_value={
                    "name": proposal.name,
                    "files_created": files_created,
                    "description_length": len(proposal_to_create.description),
                },
            )

            logger.info(f"Successfully created proposal: {proposal.name} (id={proposal.id})")
            created.append(CreatedProposalResponse(
                id=proposal.id,
                name=proposal.name,
                status=proposal.status.value,
                files_created=files_created,
            ))

        except Exception as e:
            logger.error(f"Failed to create proposal '{proposal_to_create.name}': {e}", exc_info=True)
            failed.append(FailedProposalResponse(
                name=proposal_to_create.name,
                error=str(e),
            ))

    logger.info(
        f"Batch proposal creation complete: {len(created)} created, {len(failed)} failed, "
        f"{total_tokens} tokens used"
    )
    return CreateProposalsResponse(
        created=created,
        failed=failed,
        total_tokens_used=total_tokens,
    )
