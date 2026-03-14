"""Tests for the chat service and multi-dataset query pipeline."""

import io
import re
from pathlib import Path

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient

from app.chat.schemas import ChatRequest
from app.chat.service import ChatService
from app.core.exceptions import NoDatasetsAvailableError
from app.datasets.repository import DatasetRepository
from app.datasets.service import DatasetService
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.main import app
from app.query.prompt_builder import (
    build_chat_interpretation_prompt,
    build_multi_dataset_sql_prompt,
)
from tests.conftest import MockConversationStore, MockLLMClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _extract_file_path(system: str) -> str:
    """Extract a file path from the multi-dataset prompt."""
    match = re.search(r"file: '([^']+)'", system)
    return match.group(1) if match else "unknown"


@pytest.fixture
async def multi_dataset_env(tmp_path):
    """Set up DB with TWO datasets uploaded."""
    db = DuckDBManager()
    await db.startup(":memory:")

    store = MetadataStore(db)
    await store.create_table()
    repo = DatasetRepository(store)

    from app.config import Settings

    settings = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="test",
        LLM_MODEL="test",
        UPLOAD_DIR=str(tmp_path / "uploads"),
    )
    ds_service = DatasetService(db=db, repository=repo, settings=settings)

    # Upload sales CSV
    sales_content = (FIXTURES_DIR / "sales_simple.csv").read_bytes()
    sales_file = UploadFile(filename="sales_simple.csv", file=io.BytesIO(sales_content))
    await ds_service.upload(sales_file, name="Sales")

    # Upload inventory CSV
    inv_content = (FIXTURES_DIR / "inventory.csv").read_bytes()
    inv_file = UploadFile(filename="inventory.csv", file=io.BytesIO(inv_content))
    await ds_service.upload(inv_file, name="Inventory")

    yield db, repo

    await db.shutdown()


class TestMultiDatasetPrompt:
    async def test_all_datasets_in_prompt(self, multi_dataset_env):
        db, repo = multi_dataset_env
        datasets = await repo.list_all()
        system, user = build_multi_dataset_sql_prompt(datasets, "test question", 100)

        assert "Sales" in system
        assert "Inventory" in system
        assert "fecha" in system
        assert "producto" in system or "cantidad" in system

    async def test_interpretation_with_history(self):
        from app.chat.conversation import ConversationMessage

        history = [
            ConversationMessage(role="user", content="Total sales?", timestamp="t1"),
            ConversationMessage(role="assistant", content="$50,000", timestamp="t2"),
        ]
        system, user = build_chat_interpretation_prompt(
            question="By branch?",
            sql="SELECT 1",
            result=[{"a": 1}],
            locale="es",
            history=history,
        )
        assert "Total sales?" in system
        assert "$50,000" in system
        assert "By branch?" in system


class TestChatService:
    async def test_full_pipeline(self, multi_dataset_env):
        db, repo = multi_dataset_env
        conv_store = MockConversationStore()

        call_count = 0

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                file_path = _extract_file_path(system)
                return f"SELECT COUNT(*) AS total FROM '{file_path}'"
            return "There are 20 rows."

        mock_llm = MockLLMClient(response=mock_response)
        service = ChatService(
            db=db,
            repository=repo,
            llm_client=mock_llm,
            conversation_store=conv_store,
        )

        request = ChatRequest(question="How many rows?", locale="en")
        response = await service.chat(request)

        assert response.answer == "There are 20 rows."
        assert response.conversation_id is not None
        assert response.sql is not None

    async def test_conversation_persistence(self, multi_dataset_env):
        db, repo = multi_dataset_env
        conv_store = MockConversationStore()

        call_count = 0

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                file_path = _extract_file_path(system)
                return f"SELECT COUNT(*) AS total FROM '{file_path}'"
            return f"Answer {call_count // 2}"

        mock_llm = MockLLMClient(response=mock_response)
        service = ChatService(
            db=db,
            repository=repo,
            llm_client=mock_llm,
            conversation_store=conv_store,
        )

        # First message
        r1 = await service.chat(ChatRequest(question="First question"))
        conv_id = r1.conversation_id

        # Second message with same conversation
        r2 = await service.chat(ChatRequest(question="Follow-up", conversation_id=conv_id))
        assert r2.conversation_id == conv_id

        # Verify history grew
        conv = await conv_store.get(conv_id)
        assert conv is not None
        assert len(conv.messages) == 4  # 2 user + 2 assistant

    async def test_no_datasets_error(self):
        db = DuckDBManager()
        await db.startup(":memory:")
        store = MetadataStore(db)
        await store.create_table()
        repo = DatasetRepository(store)
        conv_store = MockConversationStore()

        service = ChatService(
            db=db,
            repository=repo,
            llm_client=MockLLMClient(),
            conversation_store=conv_store,
        )

        with pytest.raises(NoDatasetsAvailableError):
            await service.chat(ChatRequest(question="test"))

        await db.shutdown()

    async def test_history_in_interpretation_prompt(self, multi_dataset_env):
        db, repo = multi_dataset_env
        conv_store = MockConversationStore()

        call_count = 0
        interpretation_system = None

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count, interpretation_system
            call_count += 1
            if call_count % 2 == 1:
                file_path = _extract_file_path(system)
                return f"SELECT 1 AS x FROM '{file_path}'"
            interpretation_system = system
            return "Answer"

        mock_llm = MockLLMClient(response=mock_response)
        service = ChatService(
            db=db,
            repository=repo,
            llm_client=mock_llm,
            conversation_store=conv_store,
        )

        r1 = await service.chat(ChatRequest(question="First question"))

        # Second call — interpretation should include history
        call_count = 0
        interpretation_system = None
        await service.chat(
            ChatRequest(question="Second question", conversation_id=r1.conversation_id)
        )

        assert interpretation_system is not None
        assert "First question" in interpretation_system


class TestChatEndpoint:
    @pytest.fixture
    async def test_client(self, tmp_path):
        """Set up the full app with mock LLM and mock conversation store."""
        db = DuckDBManager()
        await db.startup(":memory:")

        store = MetadataStore(db)
        await store.create_table()

        call_count = 0

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                file_path = _extract_file_path(system)
                return f"SELECT COUNT(*) AS total FROM '{file_path}'"
            return "There are 20 rows total."

        app.state.db = db
        app.state.metadata_store = store
        app.state.llm_client = MockLLMClient(response=mock_response)
        app.state.conversation_store = MockConversationStore()

        from app.dependencies import get_settings

        settings = get_settings()
        original = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = str(tmp_path / "uploads")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Upload a dataset first
            csv_path = FIXTURES_DIR / "sales_simple.csv"
            with open(csv_path, "rb") as f:
                await ac.post(
                    "/datasets",
                    files={"file": ("sales.csv", f, "text/csv")},
                )
            yield ac

        settings.UPLOAD_DIR = original
        await db.shutdown()

    async def test_chat_endpoint(self, test_client):
        response = await test_client.post(
            "/chat",
            json={"question": "How many rows?", "locale": "en"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "There are 20 rows total."
        assert "conversation_id" in body
        assert "sql" in body

    async def test_chat_preserves_conversation(self, test_client):
        r1 = await test_client.post("/chat", json={"question": "First"})
        conv_id = r1.json()["conversation_id"]

        r2 = await test_client.post(
            "/chat",
            json={"question": "Second", "conversation_id": conv_id},
        )
        assert r2.json()["conversation_id"] == conv_id
