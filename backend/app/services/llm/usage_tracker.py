"""LLM usage tracking service."""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.llm_usage import LLMUsage, LLMUsageCreate, LLMUsageSummary
from app.services.llm.base import LLMResponse


class LLMUsageTracker:
    """Service for tracking LLM API usage."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_usage(
        self,
        user_id: int,
        response: LLMResponse,
        operation: str,
        proposal_id: int | None = None,
        duration_ms: int | None = None,
    ) -> LLMUsage:
        """Record successful LLM usage.

        Args:
            user_id: User who made the request
            response: LLM response with usage info
            operation: Type of operation (e.g., "iterate")
            proposal_id: Optional associated proposal
            duration_ms: Request duration in milliseconds

        Returns:
            Created LLMUsage record
        """
        usage = LLMUsage(
            user_id=user_id,
            proposal_id=proposal_id,
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            operation=operation,
            success=True,
            duration_ms=duration_ms,
        )
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        return usage

    async def record_failure(
        self,
        user_id: int,
        provider: str,
        model: str,
        operation: str,
        error_message: str,
        proposal_id: int | None = None,
        duration_ms: int | None = None,
    ) -> LLMUsage:
        """Record failed LLM request.

        Args:
            user_id: User who made the request
            provider: Provider that was attempted
            model: Model that was attempted
            operation: Type of operation
            error_message: Error description
            proposal_id: Optional associated proposal
            duration_ms: Request duration in milliseconds

        Returns:
            Created LLMUsage record
        """
        usage = LLMUsage(
            user_id=user_id,
            proposal_id=proposal_id,
            provider=provider,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            operation=operation,
            success=False,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        return usage

    @asynccontextmanager
    async def track_request(
        self,
        user_id: int,
        operation: str,
        provider: str,
        model: str,
        proposal_id: int | None = None,
    ):
        """Context manager for tracking LLM requests with timing.

        Usage:
            async with tracker.track_request(user_id, "iterate", "openai", "gpt-4") as track:
                response = await provider.generate(messages)
                track.set_response(response)
        """
        tracker = _RequestTracker(
            service=self,
            user_id=user_id,
            operation=operation,
            provider=provider,
            model=model,
            proposal_id=proposal_id,
        )
        yield tracker
        await tracker.finalize()

    async def get_user_usage(
        self,
        user_id: int,
        since: datetime | None = None,
    ) -> list[LLMUsage]:
        """Get usage records for a user.

        Args:
            user_id: User ID
            since: Optional start datetime filter

        Returns:
            List of usage records
        """
        query = select(LLMUsage).where(LLMUsage.user_id == user_id)
        if since:
            query = query.where(LLMUsage.created_at >= since)
        query = query.order_by(LLMUsage.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_proposal_usage(self, proposal_id: int) -> list[LLMUsage]:
        """Get usage records for a proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            List of usage records
        """
        result = await self.session.execute(
            select(LLMUsage)
            .where(LLMUsage.proposal_id == proposal_id)
            .order_by(LLMUsage.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_summary(
        self,
        user_id: int | None = None,
        since: datetime | None = None,
    ) -> LLMUsageSummary:
        """Get usage summary statistics.

        Args:
            user_id: Optional user filter
            since: Optional start datetime filter

        Returns:
            Usage summary with aggregated statistics
        """
        query = select(LLMUsage)
        if user_id:
            query = query.where(LLMUsage.user_id == user_id)
        if since:
            query = query.where(LLMUsage.created_at >= since)

        result = await self.session.execute(query)
        records = list(result.scalars().all())

        if not records:
            return LLMUsageSummary(
                total_requests=0,
                total_tokens=0,
                total_prompt_tokens=0,
                total_completion_tokens=0,
                success_rate=0.0,
                providers={},
                operations={},
            )

        total_requests = len(records)
        successful = sum(1 for r in records if r.success)
        total_tokens = sum(r.total_tokens for r in records)
        prompt_tokens = sum(r.prompt_tokens for r in records)
        completion_tokens = sum(r.completion_tokens for r in records)

        providers: dict[str, int] = {}
        operations: dict[str, int] = {}
        for r in records:
            providers[r.provider] = providers.get(r.provider, 0) + 1
            operations[r.operation] = operations.get(r.operation, 0) + 1

        return LLMUsageSummary(
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_prompt_tokens=prompt_tokens,
            total_completion_tokens=completion_tokens,
            success_rate=successful / total_requests if total_requests > 0 else 0.0,
            providers=providers,
            operations=operations,
        )


class _RequestTracker:
    """Internal helper for tracking individual requests."""

    def __init__(
        self,
        service: LLMUsageTracker,
        user_id: int,
        operation: str,
        provider: str,
        model: str,
        proposal_id: int | None,
    ):
        self.service = service
        self.user_id = user_id
        self.operation = operation
        self.provider = provider
        self.model = model
        self.proposal_id = proposal_id
        self.start_time = time.monotonic()
        self._response: LLMResponse | None = None
        self._error: str | None = None

    def set_response(self, response: LLMResponse) -> None:
        """Set successful response."""
        self._response = response

    def set_error(self, error: str) -> None:
        """Set error message."""
        self._error = error

    async def finalize(self) -> None:
        """Finalize tracking and record usage."""
        duration_ms = int((time.monotonic() - self.start_time) * 1000)

        if self._response:
            await self.service.record_usage(
                user_id=self.user_id,
                response=self._response,
                operation=self.operation,
                proposal_id=self.proposal_id,
                duration_ms=duration_ms,
            )
        elif self._error:
            await self.service.record_failure(
                user_id=self.user_id,
                provider=self.provider,
                model=self.model,
                operation=self.operation,
                error_message=self._error,
                proposal_id=self.proposal_id,
                duration_ms=duration_ms,
            )
