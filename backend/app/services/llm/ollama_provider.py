"""Ollama LLM provider implementation for local models."""

import logging
from typing import AsyncIterator

import httpx

from app.core.config import get_settings
from app.services.llm.base import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMModelNotFoundError,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = 120.0,
    ):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (defaults to settings or localhost:11434)
            default_model: Default model to use (defaults to settings or llama3.2)
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        # Use settings if this is the configured provider, otherwise use defaults
        if settings.llm_provider == "ollama":
            self._base_url = base_url or settings.llm_base_url or "http://localhost:11434"
            self._default_model = default_model or settings.llm_model or "llama3.2"
        else:
            self._base_url = base_url or "http://localhost:11434"
            self._default_model = default_model or "llama3.2"
        self._timeout = timeout
        self._available: bool | None = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        # Lazy check - will be set on first actual call
        # Return True optimistically, errors will be caught during generation
        return True

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage to Ollama format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _check_availability(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        model = model or self._default_model

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": self._convert_messages(messages),
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                )

                if response.status_code == 404:
                    raise LLMModelNotFoundError(self.name, f"Model '{model}' not found")

                response.raise_for_status()
                data = response.json()

                # Ollama provides token counts
                usage = TokenUsage(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                )

                return LLMResponse(
                    content=data["message"]["content"],
                    model=data.get("model", model),
                    provider=self.name,
                    usage=usage,
                    finish_reason="stop" if data.get("done") else None,
                )

        except httpx.ConnectError as e:
            raise LLMProviderError(
                self.name,
                f"Cannot connect to Ollama at {self._base_url}. Is Ollama running?",
                cause=e,
            ) from e
        except httpx.TimeoutException as e:
            raise LLMProviderError(
                self.name,
                f"Request timed out after {self._timeout}s",
                cause=e,
            ) from e
        except LLMProviderError:
            raise
        except Exception as e:
            logger.exception("Ollama generation failed")
            raise LLMProviderError(self.name, f"Generation failed: {e}", cause=e) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        model = model or self._default_model

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": self._convert_messages(messages),
                        "stream": True,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                ) as response:
                    if response.status_code == 404:
                        raise LLMModelNotFoundError(self.name, f"Model '{model}' not found")

                    response.raise_for_status()

                    import json
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]

        except httpx.ConnectError as e:
            raise LLMProviderError(
                self.name,
                f"Cannot connect to Ollama at {self._base_url}. Is Ollama running?",
                cause=e,
            ) from e
        except httpx.TimeoutException as e:
            raise LLMProviderError(
                self.name,
                f"Request timed out after {self._timeout}s",
                cause=e,
            ) from e
        except LLMProviderError:
            raise
        except Exception as e:
            logger.exception("Ollama streaming failed")
            raise LLMProviderError(self.name, f"Streaming failed: {e}", cause=e) from e

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []
