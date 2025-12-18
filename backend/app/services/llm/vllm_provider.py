"""vLLM provider implementation for local high-performance inference."""

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


class VLLMProvider(LLMProvider):
    """vLLM local LLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        default_model: str = "default",
        timeout: float = 120.0,
    ):
        """Initialize vLLM provider.

        Args:
            base_url: vLLM server URL
            default_model: Default model name (vLLM usually serves one model)
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self._base_url = base_url
        if settings.llm_provider == "vllm" and settings.llm_base_url:
            self._base_url = settings.llm_base_url
        self._default_model = default_model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "vllm"

    @property
    def is_available(self) -> bool:
        # Optimistically return True, errors caught during generation
        return True

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage to OpenAI-compatible format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _get_model_name(self) -> str:
        """Get the model name from vLLM server."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/v1/models")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        return data["data"][0]["id"]
        except Exception:
            pass
        return self._default_model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        # vLLM typically serves one model, get it from the server if not specified
        if model is None:
            model = await self._get_model_name()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": self._convert_messages(messages),
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    },
                )

                if response.status_code == 404:
                    raise LLMModelNotFoundError(self.name, f"Model '{model}' not found")

                response.raise_for_status()
                data = response.json()

                choice = data["choices"][0]
                usage_data = data.get("usage", {})
                usage = TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                )

                return LLMResponse(
                    content=choice["message"]["content"],
                    model=data.get("model", model),
                    provider=self.name,
                    usage=usage,
                    finish_reason=choice.get("finish_reason"),
                )

        except httpx.ConnectError as e:
            raise LLMProviderError(
                self.name,
                f"Cannot connect to vLLM at {self._base_url}. Is vLLM running?",
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
            logger.exception("vLLM generation failed")
            raise LLMProviderError(self.name, f"Generation failed: {e}", cause=e) from e

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        # vLLM typically serves one model, get it from the server if not specified
        if model is None:
            model = await self._get_model_name()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": self._convert_messages(messages),
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    },
                ) as response:
                    if response.status_code == 404:
                        raise LLMModelNotFoundError(self.name, f"Model '{model}' not found")

                    response.raise_for_status()

                    import json
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data["choices"] and data["choices"][0].get("delta", {}).get("content"):
                                    yield data["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                continue

        except httpx.ConnectError as e:
            raise LLMProviderError(
                self.name,
                f"Cannot connect to vLLM at {self._base_url}. Is vLLM running?",
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
            logger.exception("vLLM streaming failed")
            raise LLMProviderError(self.name, f"Streaming failed: {e}", cause=e) from e

    async def get_model_info(self) -> dict | None:
        """Get information about the served model."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/v1/models")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        return data["data"][0]
        except Exception as e:
            logger.warning(f"Failed to get vLLM model info: {e}")
        return None
