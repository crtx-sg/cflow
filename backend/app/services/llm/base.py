"""LLM provider protocol and base types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator


@dataclass
class LLMMessage:
    """A message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class TokenUsage:
    """Token usage statistics for an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_complete(self) -> bool:
        """Check if the response completed normally."""
        return self.finish_reason in ("stop", "end_turn", None)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for identification."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: List of conversation messages
            model: Model to use (provider-specific default if None)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM.

        Args:
            messages: List of conversation messages
            model: Model to use (provider-specific default if None)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Yields:
            String chunks of the generated response

        Raises:
            LLMProviderError: If generation fails
        """
        ...


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, provider: str, message: str, cause: Exception | None = None):
        self.provider = provider
        self.message = message
        self.cause = cause
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMProviderError):
    """Rate limit exceeded error."""

    def __init__(self, provider: str, retry_after: float | None = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(provider, message)


class LLMAuthenticationError(LLMProviderError):
    """Authentication failed error."""

    pass


class LLMModelNotFoundError(LLMProviderError):
    """Requested model not found."""

    pass
