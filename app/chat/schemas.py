"""Pydantic models for chat endpoints."""

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""

    question: str
    locale: str = "en"
    conversation_id: str | None = None
    include_sql: bool = True


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""

    question: str
    answer: str
    sql: str | None = None
    result: list[dict[str, Any]] | None = None
    execution_time_ms: int
    conversation_id: str
