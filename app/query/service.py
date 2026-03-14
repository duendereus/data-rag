"""Query service — orchestrates the Text-to-SQL pipeline."""

import re
import time
from typing import Any

import structlog

from app.core.exceptions import DatasetNotFoundError, QueryExecutionError
from app.datasets.repository import DatasetRepository
from app.db.duckdb import DuckDBManager
from app.llm.base import LLMClient
from app.query.prompt_builder import build_interpretation_prompt, build_sql_prompt
from app.query.schemas import QueryRequest, QueryResponse

logger = structlog.get_logger()

# Pattern to strip markdown code fences from LLM output
_FENCE_RE = re.compile(r"^```(?:sql)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)


def _clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM-generated SQL."""
    cleaned = raw.strip()
    match = _FENCE_RE.match(cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


class QueryService:
    """Orchestrates: prompt → LLM → DuckDB → LLM → response."""

    def __init__(
        self,
        db: DuckDBManager,
        repository: DatasetRepository,
        llm_client: LLMClient,
        row_limit: int = 1000,
    ) -> None:
        self._db = db
        self._repo = repository
        self._llm = llm_client
        self._row_limit = row_limit

    async def run_query(
        self, dataset_id: str, request: QueryRequest
    ) -> QueryResponse:
        """Execute the full query pipeline for a dataset."""
        # Load dataset metadata
        record = await self._repo.get_by_id(dataset_id)
        if not record:
            raise DatasetNotFoundError(dataset_id)

        # Step 1: Generate SQL via LLM
        sql_system, sql_user = build_sql_prompt(
            record, request.question, self._row_limit
        )
        raw_sql = await self._llm.complete(sql_system, sql_user)
        sql = _clean_sql(raw_sql)

        logger.info("sql_generated", dataset_id=dataset_id, sql=sql)

        # Step 2: Execute SQL via DuckDB
        start = time.monotonic()
        try:
            result: list[dict[str, Any]] = await self._db.execute(sql)
        except Exception as e:
            logger.error("query_execution_failed", sql=sql, error=str(e))
            raise QueryExecutionError(sql=sql, detail=str(e)) from e
        execution_time_ms = int((time.monotonic() - start) * 1000)

        # Step 3: Interpret results via LLM
        interp_system, interp_user = build_interpretation_prompt(
            question=request.question,
            sql=sql,
            result=result,
            locale=request.locale,
        )
        answer = await self._llm.complete(interp_system, interp_user)

        return QueryResponse(
            question=request.question,
            answer=answer,
            sql=sql if request.include_sql else None,
            result=result if request.include_sql else None,
            execution_time_ms=execution_time_ms,
            dataset_id=dataset_id,
        )
