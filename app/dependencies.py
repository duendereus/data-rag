"""Dependency injection factories for FastAPI."""

from functools import lru_cache

from fastapi import Request

from app.chat.conversation import ConversationStore
from app.config import Settings
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.llm.base import LLMClient


@lru_cache
def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return Settings()


def get_db(request: Request) -> DuckDBManager:
    """Retrieve the DuckDBManager from application state."""
    return request.app.state.db


def get_metadata_store(request: Request) -> MetadataStore:
    """Retrieve the MetadataStore from application state."""
    return request.app.state.metadata_store


def get_llm_client(request: Request) -> LLMClient:
    """Retrieve the LLM client from application state."""
    return request.app.state.llm_client


def get_conversation_store(request: Request) -> ConversationStore:
    """Retrieve the conversation store from application state."""
    return request.app.state.conversation_store
