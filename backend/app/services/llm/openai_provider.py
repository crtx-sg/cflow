"""OpenAI LLM provider implementation."""

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError

from app.core.config import get_settings
from app.services.llm.base import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4",
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (uses env var if not provided)
            base_url: Optional custom base URL for API
            default_model: Default model to use
        """
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._base_url = base_url or settings.llm_base_url
        self._default_model = default_model or settings.llm_model

        self._client: AsyncOpenAI | None = None
        if self._api_key:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return self._client is not None and self._api_key is not None

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage to OpenAI format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        if not self._client:
            raise LLMProviderError(self.name, "OpenAI client not configured")

        model = model or self._default_model
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=self._convert_messages(messages),
                max_tokens=max_tokens,
                temperature=temperature,
            )

            choice = response.choices[0]
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.name,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.name, "Invalid API key") from e
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, "response") and e.response:
                retry_after = float(e.response.headers.get("retry-after", 0))
            raise LLMRateLimitError(self.name, retry_after) from e
        except APIError as e:
            raise LLMProviderError(self.name, str(e), cause=e) from e
        except Exception as e:
            logger.exception("OpenAI generation failed")
            raise LLMProviderError(self.name, f"Generation failed: {e}", cause=e) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        if not self._client:
            raise LLMProviderError(self.name, "OpenAI client not configured")

        model = model or self._default_model
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=self._convert_messages(messages),
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.name, "Invalid API key") from e
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, "response") and e.response:
                retry_after = float(e.response.headers.get("retry-after", 0))
            raise LLMRateLimitError(self.name, retry_after) from e
        except APIError as e:
            raise LLMProviderError(self.name, str(e), cause=e) from e
        except Exception as e:
            logger.exception("OpenAI streaming failed")
            raise LLMProviderError(self.name, f"Streaming failed: {e}", cause=e) from e
