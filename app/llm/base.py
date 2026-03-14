"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Port interface for LLM provider integrations."""

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Send a system + user prompt and return the LLM's text response."""
        ...

    async def stream_complete(self, system: str, user: str):
        """Streaming variant — placeholder for future implementation."""
        raise NotImplementedError("Streaming is not yet supported")
