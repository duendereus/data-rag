"""Factory to create LLM clients from application settings."""

from app.config import Settings
from app.llm.anthropic import AnthropicLLMClient
from app.llm.base import LLMClient
from app.llm.openai import OpenAILLMClient


def create_llm_client(settings: Settings) -> LLMClient:
    """Instantiate the appropriate LLM client based on configuration."""
    if settings.LLM_PROVIDER == "anthropic":
        return AnthropicLLMClient(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    if settings.LLM_PROVIDER == "openai":
        return OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            base_url=settings.OPENAI_BASE_URL,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
