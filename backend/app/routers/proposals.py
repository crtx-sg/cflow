"""Proposal lifecycle endpoints."""

import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select

from app.core.deps import CurrentUser, DbSession
from app.models import (
    ChangeProposal,
    ChangeProposalCreate,
    ChangeProposalRead,
    CommentStatus,
    Project,
    ProposalContent,
    ProposalContentRead,
    ProposalContentUpdate,
    ProposalStatus,
    ReviewComment,
    UserRole,
    ContentVersionRead,
)
from app.services.audit import AuditService
from app.services.content_versioning import ContentVersioningService
from app.services.filesystem import (
    ensure_directory,
    validate_file_path,
    validate_path,
    PathValidationError,
)
from app.services.openspec_client import openspec_client, ValidationResult
from app.services.iteration import IterationEngine, SectionGenerator

router = APIRouter(prefix="/proposals")


# Request/Response models
class ValidationResponse(BaseModel):
    passed: bool
    errors: list[str]
    warnings: list[str]
    output: str


class IterationRequest(BaseModel):
    """Request for iterating on content."""
    file_path: str
    instructions: str = ""
    model: str | None = None
    temperature: float = 0.7


class IterationResponse(BaseModel):
    """Response from iteration."""
    success: bool
    content: str | None = None
    file_path: str | None = None
    version: int | None = None
    error: str | None = None
    tokens_used: int | None = None


class GenerateSectionRequest(BaseModel):
    """Request for generating a new section."""
    section_type: str
    file_path: str
    requirements: str = ""
    instructions: str = ""
    model: str | None = None


# Helper functions
async def get_proposal_with_access(
    proposal_id: int,
    session,
    current_user,
    require_author: bool = False,
) -> ChangeProposal:
    """Get proposal and check access."""
    result = await session.execute(
        select(ChangeProposal).where(ChangeProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get project for access check
    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access
    if current_user.role != UserRole.ADMIN:
        if project.owner_id != current_user.id and proposal.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    if require_author and proposal.author_id != current_user.id:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only author can perform this action")

    return proposal


# Proposal CRUD
@router.post(
    "/projects/{project_id}/proposals",
    response_model=ChangeProposalRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal(
    project_id: int,
    proposal_data: ChangeProposalCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Create a new proposal with DRAFT status."""
    # Check project exists and user has access
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check for duplicate name
    result = await session.execute(
        select(ChangeProposal).where(
            ChangeProposal.project_id == project_id,
            ChangeProposal.name == proposal_data.name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Proposal name already exists")

    # Create proposal
    proposal = ChangeProposal(
        name=proposal_data.name,
        project_id=project_id,
        author_id=current_user.id,
        status=ProposalStatus.DRAFT,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # Create initial content files
    versioning = ContentVersioningService(session)
    await versioning.save_content(
        proposal_id=proposal.id,
        file_path="proposal.md",
        content=f"# Change: {proposal_data.name}\n\n## Why\n\n## What Changes\n\n## Impact\n",
        user_id=current_user.id,
        change_reason="Initial creation",
    )
    await versioning.save_content(
        proposal_id=proposal.id,
        file_path="tasks.md",
        content=f"# Tasks: {proposal_data.name}\n\n## 1. Implementation\n\n- [ ] 1.1 \n",
        user_id=current_user.id,
        change_reason="Initial creation",
    )

    # Audit log
    audit = AuditService(session)
    await audit.log_proposal_created(current_user.id, proposal.id, proposal.name)

    return proposal


@router.get("/projects/{project_id}/proposals", response_model=list[ChangeProposalRead])
async def list_proposals(
    project_id: int,
    current_user: CurrentUser,
    session: DbSession,
    status_filter: ProposalStatus | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[ChangeProposal]:
    """List proposals for a project."""
    # Check project access
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build query
    query = select(ChangeProposal).where(ChangeProposal.project_id == project_id)

    if status_filter:
        query = query.where(ChangeProposal.status == status_filter)

    if search:
        query = query.where(ChangeProposal.name.contains(search))

    query = query.offset(skip).limit(limit).order_by(ChangeProposal.updated_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{proposal_id}", response_model=ChangeProposalRead)
async def get_proposal(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Get proposal details."""
    return await get_proposal_with_access(proposal_id, session, current_user)


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    """Delete a proposal (DRAFT status only)."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status != ProposalStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete DRAFT proposals")

    # Delete contents and versions
    versioning = ContentVersioningService(session)
    result = await session.execute(
        select(ProposalContent).where(ProposalContent.proposal_id == proposal_id)
    )
    for content in result.scalars().all():
        await versioning.delete_content(proposal_id, content.file_path)

    # Delete proposal
    await session.delete(proposal)
    await session.commit()

    # Audit log
    audit = AuditService(session)
    await audit.log(
        user_id=current_user.id,
        action="PROPOSAL_DELETED",
        resource_type="proposal",
        resource_id=proposal_id,
    )


# Content endpoints
@router.get("/{proposal_id}/content", response_model=list[ProposalContentRead])
async def list_proposal_content(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> list[ProposalContent]:
    """List all content files for a proposal."""
    await get_proposal_with_access(proposal_id, session, current_user)

    versioning = ContentVersioningService(session)
    return await versioning.get_all_contents(proposal_id)


@router.get("/{proposal_id}/content/{file_path:path}", response_model=ProposalContentRead)
async def get_proposal_content(
    proposal_id: int,
    file_path: str,
    current_user: CurrentUser,
    session: DbSession,
) -> ProposalContent:
    """Get content for a specific file."""
    await get_proposal_with_access(proposal_id, session, current_user)

    try:
        validated_path = validate_file_path(file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    versioning = ContentVersioningService(session)
    content = await versioning.get_content(proposal_id, validated_path)

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return content


@router.put("/{proposal_id}/content/{file_path:path}", response_model=ProposalContentRead)
async def update_proposal_content(
    proposal_id: int,
    file_path: str,
    content_data: ProposalContentUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> ProposalContent:
    """Update content for a file (author only, DRAFT/REVIEW status)."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Cannot edit content in READY or MERGED status")

    try:
        validated_path = validate_file_path(file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    versioning = ContentVersioningService(session)
    content = await versioning.save_content(
        proposal_id=proposal_id,
        file_path=validated_path,
        content=content_data.content,
        user_id=current_user.id,
        change_reason=content_data.change_reason,
    )

    # Update proposal timestamp
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()

    # Audit log
    audit = AuditService(session)
    await audit.log_content_modified(current_user.id, proposal_id, validated_path, content.version)

    return content


@router.get("/{proposal_id}/content/{file_path:path}/versions", response_model=list[ContentVersionRead])
async def get_content_versions(
    proposal_id: int,
    file_path: str,
    current_user: CurrentUser,
    session: DbSession,
) -> list:
    """Get version history for a file."""
    await get_proposal_with_access(proposal_id, session, current_user)

    try:
        validated_path = validate_file_path(file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    versioning = ContentVersioningService(session)
    return await versioning.get_version_history(proposal_id, validated_path)


@router.post("/{proposal_id}/content/{file_path:path}/rollback", response_model=ProposalContentRead)
async def rollback_content(
    proposal_id: int,
    file_path: str,
    version: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ProposalContent:
    """Rollback content to a specific version."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Cannot rollback in READY or MERGED status")

    try:
        validated_path = validate_file_path(file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    versioning = ContentVersioningService(session)
    try:
        return await versioning.rollback_to_version(
            proposal_id, validated_path, version, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Status transitions
@router.post("/{proposal_id}/submit", response_model=ChangeProposalRead)
async def submit_for_review(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Submit proposal for review (DRAFT -> REVIEW)."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status != ProposalStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT proposals can be submitted")

    # Check required content exists
    versioning = ContentVersioningService(session)
    content = await versioning.get_content(proposal_id, "proposal.md")
    if not content or not content.content.strip():
        raise HTTPException(status_code=400, detail="proposal.md is required")

    old_status = proposal.status.value
    proposal.status = ProposalStatus.REVIEW
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # Audit log
    audit = AuditService(session)
    await audit.log_status_changed(current_user.id, proposal_id, old_status, proposal.status.value)

    return proposal


@router.post("/{proposal_id}/return-to-draft", response_model=ChangeProposalRead)
async def return_to_draft(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Return proposal to draft (REVIEW -> DRAFT)."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(status_code=400, detail="Only REVIEW proposals can return to draft")

    old_status = proposal.status.value
    proposal.status = ProposalStatus.DRAFT
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # Audit log
    audit = AuditService(session)
    await audit.log_status_changed(current_user.id, proposal_id, old_status, proposal.status.value)

    return proposal


@router.post("/{proposal_id}/validate-draft", response_model=ValidationResponse)
async def validate_draft(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ValidationResponse:
    """Validate draft content without writing to permanent filesystem."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user)

    # Get project for path
    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()

    # Get all content
    versioning = ContentVersioningService(session)
    contents = await versioning.get_all_contents(proposal_id)

    if not contents:
        raise HTTPException(status_code=400, detail="No content to validate")

    # Write to temp directory and validate
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create OpenSpec structure
        changes_dir = temp_path / "openspec" / "changes" / proposal.name
        changes_dir.mkdir(parents=True, exist_ok=True)

        # Write content files
        for content in contents:
            file_path = changes_dir / content.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.content)

        # Run validation
        validation_result = await openspec_client.validate_change(
            temp_path, proposal.name, strict=True
        )

    return ValidationResponse(
        passed=validation_result.passed,
        errors=validation_result.errors,
        warnings=validation_result.warnings,
        output=validation_result.output,
    )


@router.post("/{proposal_id}/mark-ready", response_model=ChangeProposalRead)
async def mark_ready(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Mark proposal as ready (REVIEW -> READY), writes to filesystem."""
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(status_code=400, detail="Only REVIEW proposals can be marked ready")

    # Check all comments resolved
    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.proposal_id == proposal_id,
            ReviewComment.status == CommentStatus.OPEN,
        )
    )
    open_comments = list(result.scalars().all())
    if open_comments:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark ready: {len(open_comments)} unresolved comments",
        )

    # Get project
    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()

    # Get all content
    versioning = ContentVersioningService(session)
    contents = await versioning.get_all_contents(proposal_id)

    # Write to project filesystem
    project_path = Path(project.local_path)
    changes_dir = project_path / "openspec" / "changes" / proposal.name

    try:
        ensure_directory(changes_dir, project_path)

        for content in contents:
            file_path = changes_dir / content.file_path
            validate_path(file_path, project_path)  # Security check
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.content)

        # Validate
        validation_result = await openspec_client.validate_change(
            project_path, proposal.name, strict=True
        )

        if not validation_result.passed:
            # Cleanup on failure
            import shutil
            if changes_dir.exists():
                shutil.rmtree(changes_dir)
            raise HTTPException(
                status_code=400,
                detail=f"Validation failed: {validation_result.output}",
            )

    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Update proposal
    old_status = proposal.status.value
    proposal.status = ProposalStatus.READY
    proposal.filesystem_path = str(changes_dir)
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # Audit log
    audit = AuditService(session)
    await audit.log_status_changed(current_user.id, proposal_id, old_status, proposal.status.value)

    return proposal


@router.post("/{proposal_id}/merge", response_model=ChangeProposalRead)
async def merge_proposal(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ChangeProposal:
    """Merge proposal (READY -> MERGED), admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    proposal = await get_proposal_with_access(proposal_id, session, current_user)

    if proposal.status != ProposalStatus.READY:
        raise HTTPException(status_code=400, detail="Only READY proposals can be merged")

    # Get project
    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()

    # Archive via OpenSpec CLI
    archive_result = await openspec_client.archive_change(
        Path(project.local_path), proposal.name
    )
    if not archive_result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive: {archive_result.stderr}",
        )

    # Update proposal
    old_status = proposal.status.value
    proposal.status = ProposalStatus.MERGED
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # Audit log
    audit = AuditService(session)
    await audit.log_status_changed(current_user.id, proposal_id, old_status, proposal.status.value)

    return proposal


# Iteration endpoints
@router.post("/{proposal_id}/iterate", response_model=IterationResponse)
async def iterate_content(
    proposal_id: int,
    request: IterationRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> IterationResponse:
    """Iterate on proposal content using LLM with reviewer feedback.

    Uses accepted comments marked for iteration as context.
    Only the proposal author can trigger iteration.
    """
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REVIEW]:
        raise HTTPException(
            status_code=400,
            detail="Can only iterate on DRAFT or REVIEW proposals"
        )

    try:
        validated_path = validate_file_path(request.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    engine = IterationEngine(session)
    result = await engine.iterate(
        proposal_id=proposal_id,
        file_path=validated_path,
        user_id=current_user.id,
        instructions=request.instructions,
        model=request.model,
        temperature=request.temperature,
    )

    # Update proposal timestamp
    if result.success:
        proposal.updated_at = datetime.utcnow()
        session.add(proposal)
        await session.commit()

    return IterationResponse(
        success=result.success,
        content=result.content,
        file_path=result.file_path,
        version=result.version,
        error=result.error,
        tokens_used=result.llm_response.usage.total_tokens if result.llm_response else None,
    )


@router.post("/{proposal_id}/generate-section", response_model=IterationResponse)
async def generate_section(
    proposal_id: int,
    request: GenerateSectionRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> IterationResponse:
    """Generate a new section for the proposal using LLM.

    Only the proposal author can generate sections.
    """
    proposal = await get_proposal_with_access(proposal_id, session, current_user, require_author=True)

    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.REVIEW]:
        raise HTTPException(
            status_code=400,
            detail="Can only generate sections for DRAFT or REVIEW proposals"
        )

    try:
        validated_path = validate_file_path(request.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    generator = SectionGenerator(session)
    result = await generator.generate_section(
        proposal_id=proposal_id,
        user_id=current_user.id,
        section_type=request.section_type,
        requirements=request.requirements,
        instructions=request.instructions,
        model=request.model,
    )

    if not result.success:
        return IterationResponse(
            success=False,
            error=result.error,
        )

    # Save the generated content
    versioning = ContentVersioningService(session)
    content = await versioning.save_content(
        proposal_id=proposal_id,
        file_path=validated_path,
        content=result.content,
        user_id=current_user.id,
        change_reason=f"Generated {request.section_type} section via LLM",
    )

    # Update proposal timestamp
    proposal.updated_at = datetime.utcnow()
    session.add(proposal)
    await session.commit()

    return IterationResponse(
        success=True,
        content=result.content,
        file_path=validated_path,
        version=content.version,
        tokens_used=result.llm_response.usage.total_tokens if result.llm_response else None,
    )
