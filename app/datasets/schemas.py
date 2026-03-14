"""Pydantic models for dataset endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SchemaColumn(BaseModel):
    """A single column's metadata."""

    column: str
    type: str
    sample: list[Any]


class DatasetResponse(BaseModel):
    """Response model for a single dataset."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    table_name: str
    row_count: int | None = None
    schema_info: list[SchemaColumn]
    file_size_bytes: int | None = None
    created_at: datetime | None = None


class DatasetListResponse(BaseModel):
    """Response model for listing datasets."""

    datasets: list[DatasetResponse]
