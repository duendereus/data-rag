"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.chat.conversation import Conversation, ConversationMessage, ConversationStore
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


class MockConversationStore(ConversationStore):
    """In-memory conversation store for testing."""

    def __init__(self) -> None:
        self._store: dict[str, list[ConversationMessage]] = {}

    async def get(self, conversation_id: str) -> Conversation | None:
        messages = self._store.get(conversation_id)
        if messages is None:
            return None
        return Conversation(id=conversation_id, messages=list(messages))

    async def append(self, conversation_id: str, message: ConversationMessage) -> None:
        if conversation_id not in self._store:
            self._store[conversation_id] = []
        self._store[conversation_id].append(message)

    async def delete(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Provide a MockLLMClient with default response."""
    return MockLLMClient()


@pytest.fixture
def mock_conversation_store() -> MockConversationStore:
    """Provide an in-memory conversation store."""
    return MockConversationStore()
