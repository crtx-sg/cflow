"""LLM provider factory with fallback chain support."""

import logging
from functools import lru_cache
from typing import Literal

from app.core.config import get_settings
from app.services.llm.base import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
)
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)

ProviderType = Literal["openai", "anthropic", "ollama", "vllm"]

# Tool-to-LLM Provider mapping
TOOL_TO_PROVIDER: dict[str, ProviderType] = {
    "claude": "anthropic",
    "cursor": "openai",
    "github-copilot": "openai",
    "windsurf": "openai",
    "cline": "anthropic",
    "amazon-q": "openai",  # Uses OpenAI-compatible API
    "gemini": "openai",  # Google AI uses OpenAI-compatible API for now
    "opencode": "openai",
    "qoder": "openai",
    "roocode": "anthropic",
    "none": None,  # Use global default
}


class LLMProviderFactory:
    """Factory for creating and managing LLM providers with fallback support."""

    _providers: dict[str, LLMProvider] = {}

    @classmethod
    def get_provider(cls, provider_type: ProviderType) -> LLMProvider:
        """Get or create an LLM provider instance.

        Args:
            provider_type: Type of provider to get

        Returns:
            LLMProvider instance
        """
        if provider_type not in cls._providers:
            cls._providers[provider_type] = cls._create_provider(provider_type)
        return cls._providers[provider_type]

    @classmethod
    def _create_provider(cls, provider_type: ProviderType) -> LLMProvider:
        """Create a new provider instance."""
        if provider_type == "openai":
            return OpenAIProvider()
        elif provider_type == "anthropic":
            return AnthropicProvider()
        elif provider_type == "ollama":
            return OllamaProvider()
        elif provider_type == "vllm":
            return VLLMProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @classmethod
    def get_available_providers(cls) -> list[LLMProvider]:
        """Get list of all configured and available providers."""
        provider_types: list[ProviderType] = ["openai", "anthropic", "ollama", "vllm"]
        available = []
        for pt in provider_types:
            try:
                provider = cls.get_provider(pt)
                if provider.is_available:
                    available.append(provider)
            except Exception:
                continue
        return available

    @classmethod
    def reset(cls) -> None:
        """Reset all cached providers. Useful for testing."""
        cls._providers.clear()


class FallbackLLMProvider(LLMProvider):
    """LLM provider with automatic fallback chain."""

    def __init__(self, providers: list[LLMProvider]):
        """Initialize with a list of providers in priority order.

        Args:
            providers: List of providers to try, in order of preference
        """
        if not providers:
            raise ValueError("At least one provider is required")
        self._providers = providers

    @property
    def name(self) -> str:
        return f"fallback({','.join(p.name for p in self._providers)})"

    @property
    def is_available(self) -> bool:
        return any(p.is_available for p in self._providers)

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        last_error: Exception | None = None

        for provider in self._providers:
            if not provider.is_available:
                logger.debug(f"Skipping unavailable provider: {provider.name}")
                continue

            try:
                logger.info(f"Attempting generation with provider: {provider.name}")
                return await provider.generate(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except LLMProviderError as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                last_error = e
                continue

        raise LLMProviderError(
            "fallback",
            f"All providers failed. Last error: {last_error}",
            cause=last_error,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        last_error: Exception | None = None

        for provider in self._providers:
            if not provider.is_available:
                continue

            try:
                logger.info(f"Attempting streaming with provider: {provider.name}")
                async for chunk in provider.generate_stream(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    yield chunk
                return
            except LLMProviderError as e:
                logger.warning(f"Provider {provider.name} streaming failed: {e}")
                last_error = e
                continue

        raise LLMProviderError(
            "fallback",
            f"All providers failed for streaming. Last error: {last_error}",
            cause=last_error,
        )


def get_provider_for_tool(tool: str) -> ProviderType | None:
    """Get the LLM provider type for a given OpenSpec tool.

    Args:
        tool: OpenSpec tool name (e.g., 'claude', 'cursor', 'github-copilot')

    Returns:
        Provider type or None if tool maps to global default
    """
    return TOOL_TO_PROVIDER.get(tool)


def get_llm_provider_for_project(openspec_tool: str | None = None) -> LLMProvider:
    """Get the LLM provider for a specific project based on its OpenSpec tool.

    Args:
        openspec_tool: The OpenSpec tool configured for the project

    Returns:
        LLMProvider instance configured for the project's tool
    """
    # If no tool or tool maps to None, use global default
    if not openspec_tool or openspec_tool == "none":
        return get_llm_provider()

    # Get the provider type for this tool
    provider_type = get_provider_for_tool(openspec_tool)
    if not provider_type:
        return get_llm_provider()

    # Build fallback chain with tool's preferred provider first
    settings = get_settings()

    # Define fallback order based on tool's preferred provider
    fallback_order: dict[str, list[ProviderType]] = {
        "openai": ["openai", "anthropic", "ollama", "vllm"],
        "anthropic": ["anthropic", "openai", "ollama", "vllm"],
        "ollama": ["ollama", "vllm", "openai", "anthropic"],
        "vllm": ["vllm", "ollama", "openai", "anthropic"],
    }

    provider_order = fallback_order.get(provider_type, ["openai"])

    # Get available providers in order
    providers = []
    for pt in provider_order:
        try:
            provider = LLMProviderFactory.get_provider(pt)
            providers.append(provider)
        except Exception as e:
            logger.debug(f"Could not create provider {pt}: {e}")

    if not providers:
        raise RuntimeError("No LLM providers available")

    # If only one provider, return it directly
    if len(providers) == 1:
        return providers[0]

    # Return fallback provider with all available providers
    return FallbackLLMProvider(providers)


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider.

    Returns the primary provider based on settings, with available
    fallback providers automatically configured.

    Returns:
        LLMProvider instance
    """
    settings = get_settings()
    primary_type = settings.llm_provider

    # Define fallback order based on primary provider
    fallback_order: dict[str, list[ProviderType]] = {
        "openai": ["openai", "anthropic", "ollama", "vllm"],
        "anthropic": ["anthropic", "openai", "ollama", "vllm"],
        "ollama": ["ollama", "vllm", "openai", "anthropic"],
        "vllm": ["vllm", "ollama", "openai", "anthropic"],
    }

    provider_order = fallback_order.get(primary_type, ["openai"])

    # Get available providers in order
    providers = []
    for pt in provider_order:
        try:
            provider = LLMProviderFactory.get_provider(pt)
            providers.append(provider)
        except Exception as e:
            logger.debug(f"Could not create provider {pt}: {e}")

    if not providers:
        raise RuntimeError("No LLM providers available")

    # If only one provider, return it directly
    if len(providers) == 1:
        return providers[0]

    # Return fallback provider with all available providers
    return FallbackLLMProvider(providers)
