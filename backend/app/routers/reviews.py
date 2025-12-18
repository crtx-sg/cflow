"""Review comment endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.core.deps import CurrentUser, DbSession
from app.models import (
    ChangeProposal,
    CommentStatus,
    Project,
    ProposalStatus,
    ReviewComment,
    ReviewCommentCreate,
    ReviewCommentRead,
    ReviewCommentUpdate,
    CommentResolve,
    CommentSelect,
    UserRole,
)
from app.services.audit import AuditService
from app.services.filesystem import validate_file_path, PathValidationError

router = APIRouter(prefix="/proposals/{proposal_id}/comments")


async def get_proposal_for_review(
    proposal_id: int,
    session,
    current_user,
) -> ChangeProposal:
    """Get proposal and check basic access for review operations."""
    result = await session.execute(
        select(ChangeProposal).where(ChangeProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get project
    result = await session.execute(
        select(Project).where(Project.id == proposal.project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access - must be project owner, proposal author, or admin
    if current_user.role != UserRole.ADMIN:
        if project.owner_id != current_user.id and proposal.author_id != current_user.id:
            # Also allow if user is a reviewer with comments on this proposal
            result = await session.execute(
                select(ReviewComment).where(
                    ReviewComment.proposal_id == proposal_id,
                    ReviewComment.reviewer_id == current_user.id,
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="Access denied")

    return proposal


@router.post("", response_model=ReviewCommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    proposal_id: int,
    comment_data: ReviewCommentCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Create a review comment (Reviewers only, REVIEW status only)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    # Only allow comments on REVIEW proposals
    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Comments can only be added to proposals in REVIEW status"
        )

    # Can't comment on your own proposal
    if proposal.author_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Authors cannot add review comments to their own proposals"
        )

    # Validate file path
    try:
        validated_path = validate_file_path(comment_data.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate parent comment if provided
    if comment_data.parent_id:
        result = await session.execute(
            select(ReviewComment).where(
                ReviewComment.id == comment_data.parent_id,
                ReviewComment.proposal_id == proposal_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Parent comment not found")

    # Create comment
    comment = ReviewComment(
        proposal_id=proposal_id,
        reviewer_id=current_user.id,
        file_path=validated_path,
        line_start=comment_data.line_start,
        line_end=comment_data.line_end,
        content=comment_data.content,
        parent_id=comment_data.parent_id,
        status=CommentStatus.OPEN,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    # Audit log
    audit = AuditService(session)
    await audit.log(
        user_id=current_user.id,
        action="COMMENT_CREATED",
        resource_type="comment",
        resource_id=comment.id,
        new_value={
            "proposal_id": proposal_id,
            "file_path": validated_path,
            "content": comment_data.content[:100],
        },
    )

    return comment


@router.get("", response_model=list[ReviewCommentRead])
async def list_comments(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
    status_filter: CommentStatus | None = None,
    file_path: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[ReviewComment]:
    """List comments for a proposal."""
    await get_proposal_for_review(proposal_id, session, current_user)

    query = select(ReviewComment).where(ReviewComment.proposal_id == proposal_id)

    if status_filter:
        query = query.where(ReviewComment.status == status_filter)

    if file_path:
        try:
            validated_path = validate_file_path(file_path)
            query = query.where(ReviewComment.file_path == validated_path)
        except PathValidationError:
            pass  # Ignore invalid paths in filter

    # Order by parent_id to group threads, then by created_at
    query = query.order_by(
        ReviewComment.parent_id.asc().nullsfirst(),
        ReviewComment.created_at.asc()
    ).offset(skip).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{comment_id}", response_model=ReviewCommentRead)
async def get_comment(
    proposal_id: int,
    comment_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Get a specific comment."""
    await get_proposal_for_review(proposal_id, session, current_user)

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return comment


@router.put("/{comment_id}", response_model=ReviewCommentRead)
async def update_comment(
    proposal_id: int,
    comment_id: int,
    update_data: ReviewCommentUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Update a comment (owner only, OPEN status only)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Comments can only be edited on proposals in REVIEW status"
        )

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only owner or admin can edit
    if comment.reviewer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only comment owner can edit")

    # Can't edit resolved comments
    if comment.status != CommentStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot edit resolved comments")

    # Update fields
    if update_data.content is not None:
        comment.content = update_data.content
    if update_data.line_start is not None:
        comment.line_start = update_data.line_start
    if update_data.line_end is not None:
        comment.line_end = update_data.line_end

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    proposal_id: int,
    comment_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    """Delete a comment (owner only, OPEN status only)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Comments can only be deleted on proposals in REVIEW status"
        )

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only owner or admin can delete
    if comment.reviewer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only comment owner can delete")

    # Can't delete resolved comments
    if comment.status != CommentStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot delete resolved comments")

    # Check for child comments (replies)
    result = await session.execute(
        select(ReviewComment).where(ReviewComment.parent_id == comment_id)
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete comment with replies"
        )

    await session.delete(comment)
    await session.commit()


@router.post("/{comment_id}/resolve", response_model=ReviewCommentRead)
async def resolve_comment(
    proposal_id: int,
    comment_id: int,
    resolve_data: CommentResolve,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Resolve a comment (Author only: ACCEPTED/REJECTED/DEFERRED)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    # Only proposal author can resolve comments
    if proposal.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only the proposal author can resolve comments"
        )

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Can't re-resolve already resolved comments (except admin)
    if comment.status != CommentStatus.OPEN and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=400,
            detail="Comment is already resolved"
        )

    # Validate status transition
    if resolve_data.status == CommentStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail="Cannot resolve comment to OPEN status"
        )

    # Update comment
    old_status = comment.status.value
    comment.status = resolve_data.status
    comment.author_response = resolve_data.author_response
    comment.resolved_at = datetime.utcnow()
    comment.resolved_by = current_user.id

    # If accepting, auto-select for iteration
    if resolve_data.status == CommentStatus.ACCEPTED:
        comment.selected_for_iteration = True

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    # Audit log
    audit = AuditService(session)
    await audit.log_comment_resolved(
        user_id=current_user.id,
        comment_id=comment_id,
        proposal_id=proposal_id,
        status=comment.status.value,
        response=comment.author_response,
    )

    return comment


@router.post("/{comment_id}/reopen", response_model=ReviewCommentRead)
async def reopen_comment(
    proposal_id: int,
    comment_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Reopen a resolved comment (Admin or original reviewer only)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    if proposal.status != ProposalStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Comments can only be reopened on proposals in REVIEW status"
        )

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only admin or original reviewer can reopen
    if comment.reviewer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admin or original reviewer can reopen"
        )

    if comment.status == CommentStatus.OPEN:
        raise HTTPException(status_code=400, detail="Comment is already open")

    # Reopen
    comment.status = CommentStatus.OPEN
    comment.resolved_at = None
    comment.resolved_by = None
    comment.selected_for_iteration = False

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return comment


@router.post("/{comment_id}/select", response_model=ReviewCommentRead)
async def toggle_comment_selection(
    proposal_id: int,
    comment_id: int,
    select_data: CommentSelect,
    current_user: CurrentUser,
    session: DbSession,
) -> ReviewComment:
    """Toggle comment selection for iteration (Author only, ACCEPTED comments)."""
    proposal = await get_proposal_for_review(proposal_id, session, current_user)

    # Only author can select comments for iteration
    if proposal.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only the proposal author can select comments for iteration"
        )

    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.id == comment_id,
            ReviewComment.proposal_id == proposal_id,
        )
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only ACCEPTED comments can be selected for iteration
    if comment.status != CommentStatus.ACCEPTED:
        raise HTTPException(
            status_code=400,
            detail="Only ACCEPTED comments can be selected for iteration"
        )

    comment.selected_for_iteration = select_data.selected_for_iteration
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return comment


@router.get("/stats", response_model=dict)
async def get_comment_stats(
    proposal_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get comment statistics for a proposal."""
    await get_proposal_for_review(proposal_id, session, current_user)

    # Count by status
    status_counts = {}
    for status_value in CommentStatus:
        result = await session.execute(
            select(ReviewComment).where(
                ReviewComment.proposal_id == proposal_id,
                ReviewComment.status == status_value,
            )
        )
        status_counts[status_value.value] = len(list(result.scalars().all()))

    # Count selected for iteration
    result = await session.execute(
        select(ReviewComment).where(
            ReviewComment.proposal_id == proposal_id,
            ReviewComment.selected_for_iteration == True,
        )
    )
    selected_count = len(list(result.scalars().all()))

    return {
        "proposal_id": proposal_id,
        "total": sum(status_counts.values()),
        "by_status": status_counts,
        "selected_for_iteration": selected_count,
        "all_resolved": status_counts.get("open", 0) == 0,
    }
