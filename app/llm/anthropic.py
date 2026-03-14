"""Anthropic Claude LLM client adapter."""

import anthropic
import structlog

from app.core.exceptions import LLMError
from app.llm.base import LLMClient

logger = structlog.get_logger()


class AnthropicLLMClient(LLMClient):
    """LLM client using the Anthropic SDK."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 2048) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        """Send a prompt to Claude and return the text response."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("anthropic_api_error", detail=str(e))
            raise LLMError(detail=str(e)) from e
