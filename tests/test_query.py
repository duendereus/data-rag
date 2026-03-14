"""Tests for the query pipeline."""

import io
from pathlib import Path

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import DatasetNotFoundError, QueryExecutionError
from app.datasets.repository import DatasetRepository
from app.datasets.service import DatasetService
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.main import app
from app.query.schemas import QueryRequest
from app.query.service import QueryService, _clean_sql
from tests.conftest import MockLLMClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SALES_CSV = str(FIXTURES_DIR / "sales_simple.csv")


class TestCleanSQL:
    def test_plain_sql(self):
        assert _clean_sql("SELECT 1") == "SELECT 1"

    def test_strips_whitespace(self):
        assert _clean_sql("  SELECT 1  \n") == "SELECT 1"

    def test_strips_markdown_fences(self):
        raw = "```sql\nSELECT * FROM t\n```"
        assert _clean_sql(raw) == "SELECT * FROM t"

    def test_strips_fences_without_lang(self):
        raw = "```\nSELECT 1\n```"
        assert _clean_sql(raw) == "SELECT 1"


@pytest.fixture
async def setup_query_env(tmp_path):
    """Set up DB, upload a dataset, and return (db, repository, dataset_id)."""
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

    csv_content = (FIXTURES_DIR / "sales_simple.csv").read_bytes()
    upload_file = UploadFile(
        filename="sales_simple.csv",
        file=io.BytesIO(csv_content),
    )
    dataset_response = await ds_service.upload(upload_file, name="Test Sales")

    yield db, repo, dataset_response.id

    await db.shutdown()


class TestQueryService:
    async def test_full_pipeline(self, setup_query_env):
        db, repo, dataset_id = setup_query_env

        call_count = 0

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Extract file path from "located at: '<path>'"
                import re

                match = re.search(r"located at: '([^']+)'", system)
                file_path = match.group(1) if match else "unknown"
                return (
                    "SELECT sucursal, SUM(ventas) AS total_ventas "
                    f"FROM '{file_path}' "
                    "GROUP BY sucursal ORDER BY total_ventas DESC LIMIT 3"
                )
            return "CDMX fue la sucursal con mas ventas."

        mock_llm = MockLLMClient(response=mock_response)
        service = QueryService(db=db, repository=repo, llm_client=mock_llm)

        request = QueryRequest(
            question="Cual sucursal tuvo mas ventas?",
            locale="es",
        )
        response = await service.run_query(dataset_id, request)

        assert response.answer == "CDMX fue la sucursal con mas ventas."
        assert response.sql is not None
        assert "sucursal" in response.sql
        assert response.execution_time_ms >= 0
        assert len(response.result) == 3

    async def test_invalid_sql_raises_error(self, setup_query_env):
        db, repo, dataset_id = setup_query_env

        mock_llm = MockLLMClient(response="THIS IS NOT VALID SQL AT ALL")
        service = QueryService(db=db, repository=repo, llm_client=mock_llm)

        request = QueryRequest(question="test")

        with pytest.raises(QueryExecutionError):
            await service.run_query(dataset_id, request)

    async def test_dataset_not_found(self, setup_query_env):
        db, repo, _ = setup_query_env

        mock_llm = MockLLMClient()
        service = QueryService(db=db, repository=repo, llm_client=mock_llm)

        with pytest.raises(DatasetNotFoundError):
            await service.run_query("ds_nonexistent", QueryRequest(question="test"))


class TestQueryEndpoint:
    @pytest.fixture
    async def test_client(self, tmp_path):
        """Set up the full app with mock LLM for endpoint testing."""
        db = DuckDBManager()
        await db.startup(":memory:")

        store = MetadataStore(db)
        await store.create_table()

        call_count = 0

        def mock_response(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                import re

                match = re.search(r"located at: '([^']+)'", system)
                file_path = match.group(1) if match else "unknown"
                return f"SELECT COUNT(*) AS total FROM '{file_path}'"
            return "There are 20 rows total."

        app.state.db = db
        app.state.metadata_store = store
        app.state.llm_client = MockLLMClient(response=mock_response)

        from app.dependencies import get_settings

        settings = get_settings()
        original = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = str(tmp_path / "uploads")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            csv_path = FIXTURES_DIR / "sales_simple.csv"
            with open(csv_path, "rb") as f:
                resp = await ac.post(
                    "/datasets",
                    files={"file": ("sales.csv", f, "text/csv")},
                )
            dataset_id = resp.json()["id"]
            yield ac, dataset_id

        settings.UPLOAD_DIR = original
        await db.shutdown()

    async def test_query_endpoint(self, test_client):
        client, dataset_id = test_client
        response = await client.post(
            f"/datasets/{dataset_id}/query",
            json={"question": "How many rows?", "locale": "en"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "There are 20 rows total."
        assert "sql" in body
