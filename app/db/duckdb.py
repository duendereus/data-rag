"""DuckDB connection management and async query execution."""

import asyncio
from pathlib import Path

import duckdb
import structlog

logger = structlog.get_logger()


class DuckDBManager:
    """Manages DuckDB connections with async execution via thread delegation."""

    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = asyncio.Lock()

    async def startup(self, db_path: str) -> None:
        """Open the DuckDB database, creating parent dirs if needed."""
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = await asyncio.to_thread(duckdb.connect, db_path)
        logger.info("duckdb_started", path=db_path)

    async def shutdown(self) -> None:
        """Close the DuckDB connection."""
        if self._conn:
            await asyncio.to_thread(self._conn.close)
            self._conn = None
            logger.info("duckdb_closed")

    async def execute(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute SQL and return results as a list of dicts."""
        async with self._lock:
            return await asyncio.to_thread(self._execute_sync, sql, params)

    def _execute_sync(self, sql: str, params: list | None = None) -> list[dict]:
        """Synchronous execution — called inside asyncio.to_thread."""
        assert self._conn is not None, "DuckDB connection not initialized"
        if params:
            result = self._conn.execute(sql, params)
        else:
            result = self._conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    async def describe_table(self, file_path: str) -> list[dict]:
        """Run DESCRIBE on a CSV/file to extract column metadata."""
        sql = f"DESCRIBE SELECT * FROM '{file_path}'"
        return await self.execute(sql)

    async def sample_rows(self, file_path: str, limit: int = 5) -> list[dict]:
        """Return the first N rows from a file."""
        sql = f"SELECT * FROM '{file_path}' LIMIT {limit}"
        return await self.execute(sql)

    async def count_rows(self, file_path: str) -> int:
        """Return the total row count for a file."""
        sql = f"SELECT COUNT(*) AS cnt FROM '{file_path}'"
        result = await self.execute(sql)
        return result[0]["cnt"]
