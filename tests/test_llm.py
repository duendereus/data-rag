"""Tests for LLM client layer."""

import pytest

from app.config import Settings
from app.llm.anthropic import AnthropicLLMClient
from app.llm.factory import create_llm_client
from app.llm.openai import OpenAILLMClient
from tests.conftest import MockLLMClient


class TestMockLLMClient:
    async def test_returns_string_response(self):
        client = MockLLMClient(response="SELECT 1")
        result = await client.complete("system", "user")
        assert result == "SELECT 1"

    async def test_records_calls(self):
        client = MockLLMClient()
        await client.complete("sys prompt", "user query")
        assert len(client.calls) == 1
        assert client.calls[0] == ("sys prompt", "user query")

    async def test_callable_response(self):
        client = MockLLMClient(response=lambda s, u: f"echo: {u}")
        result = await client.complete("sys", "hello")
        assert result == "echo: hello"


class TestFactory:
    def test_creates_anthropic_client(self):
        settings = Settings(
            LLM_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-ant-test",
            LLM_MODEL="claude-sonnet-4-20250514",
        )
        client = create_llm_client(settings)
        assert isinstance(client, AnthropicLLMClient)

    def test_creates_openai_client(self):
        settings = Settings(
            LLM_PROVIDER="openai",
            OPENAI_API_KEY="sk-test",
            LLM_MODEL="gpt-4o",
        )
        client = create_llm_client(settings)
        assert isinstance(client, OpenAILLMClient)

    def test_raises_for_unknown_provider(self):
        settings = Settings(
            LLM_PROVIDER="unknown",
            LLM_MODEL="test",
        )
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_client(settings)
