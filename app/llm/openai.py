"""OpenAI (and compatible providers) LLM client adapter."""

import openai
import structlog

from app.core.exceptions import LLMError
from app.llm.base import LLMClient

logger = structlog.get_logger()


class OpenAILLMClient(LLMClient):
    """LLM client using the OpenAI SDK. Supports custom base_url for compatible providers."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        base_url: str | None = None,
    ) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        """Send a prompt to OpenAI and return the text response."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            logger.error("openai_api_error", detail=str(e))
            raise LLMError(detail=str(e)) from e
