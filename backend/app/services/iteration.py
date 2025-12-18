"""Iteration engine for LLM-powered content improvement."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import (
    ChangeProposal,
    ProposalContent,
    ReviewComment,
    CommentStatus,
    ProposalStatus,
)
from app.services.llm import (
    get_llm_provider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
)
from app.services.llm.usage_tracker import LLMUsageTracker
from app.services.content_versioning import ContentVersioningService

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """Result of an iteration operation."""

    success: bool
    content: str | None = None
    file_path: str | None = None
    version: int | None = None
    llm_response: LLMResponse | None = None
    error: str | None = None
    validation_passed: bool | None = None
    validation_errors: list[str] | None = None


class IterationEngine:
    """Engine for iterating on proposal content using LLM."""

    # Meta-prompt template for content iteration
    META_PROMPT = """You are an expert technical writer helping to improve compliance documentation.

## Context
You are working on a change proposal for a compliance-critical system.

## Current Content
The current draft of the document is below:

```
{current_content}
```

## Reviewer Feedback
The following comments have been accepted by the author and should be addressed:

{accepted_comments}

## Instructions from Author
{author_instructions}

## Task
Please revise the document to address all the accepted reviewer feedback while following the author's instructions.

Maintain the same format and structure unless changes are specifically requested.
Be precise and thorough. Ensure all feedback points are addressed.

Return ONLY the revised document content, without any explanatory text or markdown code blocks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.content_service = ContentVersioningService(session)
        self.usage_tracker = LLMUsageTracker(session)

    async def iterate(
        self,
        proposal_id: int,
        file_path: str,
        user_id: int,
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> IterationResult:
        """Iterate on proposal content using LLM and reviewer feedback.

        Args:
            proposal_id: ID of the proposal
            file_path: Path to the file to iterate on
            user_id: ID of the user triggering iteration
            instructions: Additional instructions from the author
            model: Optional model override
            temperature: LLM temperature parameter

        Returns:
            IterationResult with updated content or error
        """
        # Validate proposal exists and is in correct state
        result = await self.session.execute(
            select(ChangeProposal).where(ChangeProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()

        if not proposal:
            return IterationResult(success=False, error="Proposal not found")

        if proposal.status not in (ProposalStatus.DRAFT, ProposalStatus.REVIEW):
            return IterationResult(
                success=False,
                error=f"Cannot iterate on proposal in {proposal.status.value} status",
            )

        # Validate user is the author
        if proposal.author_id != user_id:
            return IterationResult(
                success=False,
                error="Only the proposal author can trigger iteration",
            )

        # Get current content
        content_record = await self.content_service.get_content(proposal_id, file_path)
        if not content_record:
            return IterationResult(
                success=False,
                error=f"Content not found for file: {file_path}",
            )

        # Get accepted comments for this file
        accepted_comments = await self._get_accepted_comments(proposal_id, file_path)

        if not accepted_comments and not instructions:
            return IterationResult(
                success=False,
                error="No accepted comments or instructions provided for iteration",
            )

        # Build the prompt
        prompt = self._build_prompt(
            current_content=content_record.content,
            accepted_comments=accepted_comments,
            author_instructions=instructions,
        )

        # Get LLM provider and generate
        provider = get_llm_provider()
        settings_model = model or "gpt-4"

        try:
            async with self.usage_tracker.track_request(
                user_id=user_id,
                operation="iterate",
                provider=provider.name,
                model=settings_model,
                proposal_id=proposal_id,
            ) as tracker:
                messages = [
                    LLMMessage(role="user", content=prompt),
                ]

                response = await provider.generate(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=8192,
                )
                tracker.set_response(response)

        except LLMProviderError as e:
            logger.error(f"LLM iteration failed: {e}")
            return IterationResult(
                success=False,
                error=f"LLM generation failed: {e.message}",
            )

        # Save the generated content
        new_content = response.content.strip()
        updated_record = await self.content_service.save_content(
            proposal_id=proposal_id,
            file_path=file_path,
            content=new_content,
            user_id=user_id,
            change_reason=f"LLM iteration: {instructions[:100] if instructions else 'Addressed reviewer feedback'}",
        )

        # Mark addressed comments as deferred (they've been processed)
        await self._mark_comments_processed(proposal_id, file_path)

        return IterationResult(
            success=True,
            content=new_content,
            file_path=file_path,
            version=updated_record.version,
            llm_response=response,
        )

    async def iterate_stream(
        self,
        proposal_id: int,
        file_path: str,
        user_id: int,
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ):
        """Stream iteration content using LLM.

        Yields content chunks as they are generated.
        After streaming completes, saves the content automatically.
        """
        # Validate proposal and permissions (same as iterate)
        result = await self.session.execute(
            select(ChangeProposal).where(ChangeProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()

        if not proposal:
            yield {"error": "Proposal not found"}
            return

        if proposal.status not in (ProposalStatus.DRAFT, ProposalStatus.REVIEW):
            yield {"error": f"Cannot iterate on proposal in {proposal.status.value} status"}
            return

        if proposal.author_id != user_id:
            yield {"error": "Only the proposal author can trigger iteration"}
            return

        # Get current content
        content_record = await self.content_service.get_content(proposal_id, file_path)
        if not content_record:
            yield {"error": f"Content not found for file: {file_path}"}
            return

        # Get accepted comments
        accepted_comments = await self._get_accepted_comments(proposal_id, file_path)

        if not accepted_comments and not instructions:
            yield {"error": "No accepted comments or instructions provided"}
            return

        # Build prompt
        prompt = self._build_prompt(
            current_content=content_record.content,
            accepted_comments=accepted_comments,
            author_instructions=instructions,
        )

        # Stream from LLM
        provider = get_llm_provider()
        full_content = ""

        try:
            messages = [LLMMessage(role="user", content=prompt)]

            async for chunk in provider.generate_stream(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=8192,
            ):
                full_content += chunk
                yield {"chunk": chunk}

            # Save the complete content
            updated_record = await self.content_service.save_content(
                proposal_id=proposal_id,
                file_path=file_path,
                content=full_content.strip(),
                user_id=user_id,
                change_reason=f"LLM iteration (streamed): {instructions[:100] if instructions else 'Addressed reviewer feedback'}",
            )

            await self._mark_comments_processed(proposal_id, file_path)

            yield {
                "complete": True,
                "version": updated_record.version,
                "file_path": file_path,
            }

        except LLMProviderError as e:
            logger.error(f"LLM streaming iteration failed: {e}")
            yield {"error": f"LLM generation failed: {e.message}"}

    async def _get_accepted_comments(
        self, proposal_id: int, file_path: str | None = None
    ) -> list[ReviewComment]:
        """Get accepted comments for iteration context."""
        query = select(ReviewComment).where(
            ReviewComment.proposal_id == proposal_id,
            ReviewComment.status == CommentStatus.ACCEPTED,
            ReviewComment.selected_for_iteration == True,
        )
        if file_path:
            query = query.where(ReviewComment.file_path == file_path)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _mark_comments_processed(
        self, proposal_id: int, file_path: str | None = None
    ) -> None:
        """Clear selection flag on processed comments."""
        query = select(ReviewComment).where(
            ReviewComment.proposal_id == proposal_id,
            ReviewComment.selected_for_iteration == True,
        )
        if file_path:
            query = query.where(ReviewComment.file_path == file_path)

        result = await self.session.execute(query)
        for comment in result.scalars().all():
            comment.selected_for_iteration = False
            self.session.add(comment)

        await self.session.commit()

    def _build_prompt(
        self,
        current_content: str,
        accepted_comments: list[ReviewComment],
        author_instructions: str,
    ) -> str:
        """Build the iteration prompt."""
        # Format accepted comments
        if accepted_comments:
            comments_text = "\n".join(
                f"- [{c.file_path}:{c.line_start or 'general'}] {c.content}"
                + (f"\n  Author response: {c.author_response}" if c.author_response else "")
                for c in accepted_comments
            )
        else:
            comments_text = "No specific comments to address."

        return self.META_PROMPT.format(
            current_content=current_content,
            accepted_comments=comments_text,
            author_instructions=author_instructions or "No additional instructions.",
        )


class SectionGenerator:
    """Generate new proposal sections using LLM."""

    SECTION_PROMPT = """You are an expert technical writer creating compliance documentation.

## Task
Generate a {section_type} section for a change proposal with the following details:

## Proposal Context
- Name: {proposal_name}
- Description: {proposal_description}

## Requirements
{requirements}

## Instructions
{instructions}

Generate a well-structured {section_type} section that is:
- Clear and precise
- Technically accurate
- Compliant with documentation standards

Return ONLY the section content, without any explanatory text."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.usage_tracker = LLMUsageTracker(session)

    async def generate_section(
        self,
        proposal_id: int,
        user_id: int,
        section_type: str,
        requirements: str = "",
        instructions: str = "",
        model: str | None = None,
    ) -> IterationResult:
        """Generate a new section for a proposal.

        Args:
            proposal_id: ID of the proposal
            user_id: ID of the user
            section_type: Type of section (e.g., "design", "implementation", "testing")
            requirements: Specific requirements for the section
            instructions: Additional generation instructions
            model: Optional model override

        Returns:
            IterationResult with generated content
        """
        # Get proposal details
        result = await self.session.execute(
            select(ChangeProposal).where(ChangeProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()

        if not proposal:
            return IterationResult(success=False, error="Proposal not found")

        if proposal.author_id != user_id:
            return IterationResult(
                success=False,
                error="Only the proposal author can generate sections",
            )

        # Build prompt
        prompt = self.SECTION_PROMPT.format(
            section_type=section_type,
            proposal_name=proposal.name,
            proposal_description=proposal.description or "No description provided",
            requirements=requirements or "No specific requirements",
            instructions=instructions or "Follow standard documentation practices",
        )

        # Generate
        provider = get_llm_provider()
        settings_model = model or "gpt-4"

        try:
            async with self.usage_tracker.track_request(
                user_id=user_id,
                operation="generate_section",
                provider=provider.name,
                model=settings_model,
                proposal_id=proposal_id,
            ) as tracker:
                messages = [LLMMessage(role="user", content=prompt)]
                response = await provider.generate(
                    messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=4096,
                )
                tracker.set_response(response)

            return IterationResult(
                success=True,
                content=response.content.strip(),
                llm_response=response,
            )

        except LLMProviderError as e:
            return IterationResult(
                success=False,
                error=f"Generation failed: {e.message}",
            )
