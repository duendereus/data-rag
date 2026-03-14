"""Pydantic models for query endpoints."""

from typing import Any

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for querying a dataset."""

    question: str
    locale: str = "en"
    include_sql: bool = True


class QueryResponse(BaseModel):
    """Response model for a query result."""

    question: str
    answer: str
    sql: str | None = None
    result: list[dict[str, Any]] | None = None
    execution_time_ms: int
    dataset_id: str
