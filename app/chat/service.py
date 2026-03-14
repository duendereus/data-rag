"""Chat service — multi-dataset queries with conversation history."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.chat.conversation import ConversationMessage, ConversationStore
from app.chat.schemas import ChatRequest, ChatResponse
from app.core.exceptions import NoDatasetsAvailableError, QueryExecutionError
from app.datasets.repository import DatasetRepository
from app.db.duckdb import DuckDBManager
from app.llm.base import LLMClient
from app.query.prompt_builder import (
    build_chat_interpretation_prompt,
    build_multi_dataset_sql_prompt,
)
from app.query.service import _clean_sql

logger = structlog.get_logger()


class ChatService:
    """Orchestrates multi-dataset queries with conversation context."""

    def __init__(
        self,
        db: DuckDBManager,
        repository: DatasetRepository,
        llm_client: LLMClient,
        conversation_store: ConversationStore,
        row_limit: int = 1000,
    ) -> None:
        self._db = db
        self._repo = repository
        self._llm = llm_client
        self._conversations = conversation_store
        self._row_limit = row_limit

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Execute a chat query across all available datasets."""
        # Resolve conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Load conversation history
        conversation = await self._conversations.get(conversation_id)
        history = conversation.messages if conversation else []

        # Load ALL datasets
        datasets = await self._repo.list_all()
        if not datasets:
            raise NoDatasetsAvailableError()

        # Step 1: Generate SQL with all dataset schemas
        sql_system, sql_user = build_multi_dataset_sql_prompt(
            datasets, request.question, self._row_limit
        )
        raw_sql = await self._llm.complete(sql_system, sql_user)
        sql = _clean_sql(raw_sql)

        logger.info("chat_sql_generated", conversation_id=conversation_id, sql=sql)

        # Step 2: Execute SQL via DuckDB
        start = time.monotonic()
        try:
            result: list[dict[str, Any]] = await self._db.execute(sql)
        except Exception as e:
            logger.error("chat_query_failed", sql=sql, error=str(e))
            raise QueryExecutionError(sql=sql, detail=str(e)) from e
        execution_time_ms = int((time.monotonic() - start) * 1000)

        # Step 3: Interpret with conversation history
        interp_system, interp_user = build_chat_interpretation_prompt(
            question=request.question,
            sql=sql,
            result=result,
            locale=request.locale,
            history=history,
        )
        answer = await self._llm.complete(interp_system, interp_user)

        # Step 4: Save to conversation history
        now = datetime.now(UTC).isoformat()
        await self._conversations.append(
            conversation_id,
            ConversationMessage(role="user", content=request.question, timestamp=now),
        )
        await self._conversations.append(
            conversation_id,
            ConversationMessage(role="assistant", content=answer, timestamp=now),
        )

        return ChatResponse(
            question=request.question,
            answer=answer,
            sql=sql if request.include_sql else None,
            result=result if request.include_sql else None,
            execution_time_ms=execution_time_ms,
            conversation_id=conversation_id,
        )
