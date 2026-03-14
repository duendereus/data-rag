"""Conversation history storage — port and Redis adapter."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()


@dataclass
class ConversationMessage:
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str  # ISO 8601


@dataclass
class Conversation:
    """A conversation with its full message history."""

    id: str
    messages: list[ConversationMessage]


class ConversationStore(ABC):
    """Abstract port for conversation persistence."""

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None:
        """Retrieve a conversation by ID."""
        ...

    @abstractmethod
    async def append(self, conversation_id: str, message: ConversationMessage) -> None:
        """Append a message to a conversation."""
        ...

    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        ...


class RedisConversationStore(ConversationStore):
    """Redis-backed conversation store using lists."""

    def __init__(self, redis: aioredis.Redis, ttl_hours: int = 24) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_hours * 3600

    def _key(self, conversation_id: str) -> str:
        return f"conv:{conversation_id}"

    async def get(self, conversation_id: str) -> Conversation | None:
        """Retrieve all messages for a conversation."""
        key = self._key(conversation_id)
        raw_messages = await self._redis.lrange(key, 0, -1)
        if not raw_messages:
            return None
        messages = [ConversationMessage(**json.loads(m)) for m in raw_messages]
        return Conversation(id=conversation_id, messages=messages)

    async def append(self, conversation_id: str, message: ConversationMessage) -> None:
        """Append a message and refresh TTL."""
        key = self._key(conversation_id)
        await self._redis.rpush(key, json.dumps(asdict(message)))
        await self._redis.expire(key, self._ttl_seconds)

    async def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        await self._redis.delete(self._key(conversation_id))
        logger.info("conversation_deleted", conversation_id=conversation_id)
