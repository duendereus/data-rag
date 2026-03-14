"""Shared test fixtures."""

from collections.abc import Callable

import pytest

from app.llm.base import LLMClient


class MockLLMClient(LLMClient):
    """Deterministic LLM client for testing."""

    def __init__(self, response: str | Callable[[str, str], str] = "mock response") -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str) -> str:
        """Record the call and return a predetermined response."""
        self.calls.append((system, user))
        if callable(self._response):
            return self._response(system, user)
        return self._response


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Provide a MockLLMClient with default response."""
    return MockLLMClient()
