"""Anthropic LLM provider implementation."""

import logging
from typing import AsyncIterator

from anthropic import AsyncAnthropic, APIError, AuthenticationError, RateLimitError

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


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-3-5-sonnet-20241022",
    ):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            default_model: Default model to use
        """
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._default_model = default_model

        self._client: AsyncAnthropic | None = None
        if self._api_key:
            self._client = AsyncAnthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return self._client is not None and self._api_key is not None

    def _prepare_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[dict]]:
        """Separate system message and convert to Anthropic format.

        Anthropic requires system message to be passed separately.
        """
        system_message = None
        conversation = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        return system_message, conversation

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        if not self._client:
            raise LLMProviderError(self.name, "Anthropic client not configured")

        model = model or self._default_model
        system_message, conversation = self._prepare_messages(messages)

        try:
            kwargs = {
                "model": model,
                "messages": conversation,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_message:
                kwargs["system"] = system_message

            response = await self._client.messages.create(**kwargs)

            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            # Extract text content from response
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.name,
                usage=usage,
                finish_reason=response.stop_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.name, "Invalid API key") from e
        except RateLimitError as e:
            raise LLMRateLimitError(self.name) from e
        except APIError as e:
            raise LLMProviderError(self.name, str(e), cause=e) from e
        except Exception as e:
            logger.exception("Anthropic generation failed")
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
            raise LLMProviderError(self.name, "Anthropic client not configured")

        model = model or self._default_model
        system_message, conversation = self._prepare_messages(messages)

        try:
            kwargs = {
                "model": model,
                "messages": conversation,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_message:
                kwargs["system"] = system_message

            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.name, "Invalid API key") from e
        except RateLimitError as e:
            raise LLMRateLimitError(self.name) from e
        except APIError as e:
            raise LLMProviderError(self.name, str(e), cause=e) from e
        except Exception as e:
            logger.exception("Anthropic streaming failed")
            raise LLMProviderError(self.name, f"Streaming failed: {e}", cause=e) from e
