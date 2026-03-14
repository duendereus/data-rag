"""Dataset metadata persistence using DuckDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db.duckdb import DuckDBManager

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dataset_metadata (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    table_name VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    schema_json VARCHAR NOT NULL,
    sample_json VARCHAR NOT NULL,
    row_count INTEGER,
    file_size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT current_timestamp
)
"""


@dataclass
class DatasetRecord:
    """Internal representation of a dataset's metadata."""

    id: str
    name: str
    table_name: str
    file_path: str
    schema_json: str
    sample_json: str
    description: str | None = None
    row_count: int | None = None
    file_size_bytes: int | None = None
    created_at: datetime | None = None


class MetadataStore:
    """CRUD operations for dataset metadata stored in DuckDB."""

    def __init__(self, db: DuckDBManager) -> None:
        self._db = db

    async def create_table(self) -> None:
        """Ensure the metadata table exists."""
        await self._db.execute(CREATE_TABLE_SQL)

    async def save(self, record: DatasetRecord) -> None:
        """Insert a new dataset metadata record."""
        sql = """
            INSERT INTO dataset_metadata
                (id, name, description, table_name, file_path, schema_json, sample_json,
                 row_count, file_size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql,
            [
                record.id,
                record.name,
                record.description,
                record.table_name,
                record.file_path,
                record.schema_json,
                record.sample_json,
                record.row_count,
                record.file_size_bytes,
                record.created_at or datetime.now(),
            ],
        )

    async def get_by_id(self, dataset_id: str) -> DatasetRecord | None:
        """Retrieve a single dataset by ID. Returns None if not found."""
        rows = await self._db.execute("SELECT * FROM dataset_metadata WHERE id = ?", [dataset_id])
        if not rows:
            return None
        return self._row_to_record(rows[0])

    async def list_all(self) -> list[DatasetRecord]:
        """Retrieve all datasets, ordered by creation date descending."""
        rows = await self._db.execute("SELECT * FROM dataset_metadata ORDER BY created_at DESC")
        return [self._row_to_record(row) for row in rows]

    async def delete_by_id(self, dataset_id: str) -> bool:
        """Delete a dataset by ID. Returns True if a row was deleted."""
        before = await self._db.execute(
            "SELECT COUNT(*) AS cnt FROM dataset_metadata WHERE id = ?", [dataset_id]
        )
        if before[0]["cnt"] == 0:
            return False
        await self._db.execute("DELETE FROM dataset_metadata WHERE id = ?", [dataset_id])
        return True

    @staticmethod
    def _row_to_record(row: dict) -> DatasetRecord:
        """Convert a dict row from DuckDB into a DatasetRecord."""
        return DatasetRecord(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            table_name=row["table_name"],
            file_path=row["file_path"],
            schema_json=row["schema_json"],
            sample_json=row["sample_json"],
            row_count=row.get("row_count"),
            file_size_bytes=row.get("file_size_bytes"),
            created_at=row.get("created_at"),
        )
