"""HTTP endpoints for the chat interface."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.chat.conversation import ConversationStore
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import ChatService
from app.config import Settings
from app.datasets.repository import DatasetRepository
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.dependencies import (
    get_conversation_store,
    get_db,
    get_llm_client,
    get_metadata_store,
    get_settings,
)
from app.llm.base import LLMClient

router = APIRouter(tags=["chat"])


def _get_chat_service(
    db: Annotated[DuckDBManager, Depends(get_db)],
    store: Annotated[MetadataStore, Depends(get_metadata_store)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    conversation_store: Annotated[ConversationStore, Depends(get_conversation_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    """Build a ChatService with injected dependencies."""
    return ChatService(
        db=db,
        repository=DatasetRepository(store),
        llm_client=llm_client,
        conversation_store=conversation_store,
        row_limit=settings.QUERY_RESULT_LIMIT,
    )


ChatServiceDep = Annotated[ChatService, Depends(_get_chat_service)]
ConversationStoreDep = Annotated[ConversationStore, Depends(get_conversation_store)]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, service: ChatServiceDep) -> ChatResponse:
    """Send a natural language question across all datasets."""
    return await service.chat(request)


@router.get("/chat/{conversation_id}")
async def get_conversation(conversation_id: str, store: ConversationStoreDep) -> dict:
    """Get the message history for a conversation."""
    conversation = await store.get(conversation_id)
    if not conversation:
        return {"conversation_id": conversation_id, "messages": []}
    return {
        "conversation_id": conversation_id,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in conversation.messages
        ],
    }


@router.delete("/chat/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, store: ConversationStoreDep) -> None:
    """Delete a conversation's history."""
    await store.delete(conversation_id)
