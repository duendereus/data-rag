"""Tests for dataset endpoints and service."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
async def test_app(tmp_path):
    """Configure the app with in-memory DB and temp upload dir for testing."""
    db = DuckDBManager()
    await db.startup(":memory:")

    store = MetadataStore(db)
    await store.create_table()

    app.state.db = db
    app.state.metadata_store = store
    app.state.llm_client = None  # not needed for dataset tests
    app.state._test_upload_dir = str(tmp_path / "uploads")

    # Patch settings for upload dir
    from app.dependencies import get_settings

    settings = get_settings()
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(tmp_path / "uploads")

    yield app

    settings.UPLOAD_DIR = original_upload_dir
    await db.shutdown()


@pytest.fixture
async def client(test_app):
    """Provide an async HTTP client for the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUpload:
    async def test_upload_csv(self, client):
        csv_path = FIXTURES_DIR / "sales_simple.csv"
        with open(csv_path, "rb") as f:
            response = await client.post(
                "/datasets",
                files={"file": ("sales_simple.csv", f, "text/csv")},
                data={"name": "Sales Q1"},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Sales Q1"
        assert body["row_count"] == 20
        assert len(body["schema_info"]) == 4
        column_names = [c["column"] for c in body["schema_info"]]
        assert "fecha" in column_names
        assert "ventas" in column_names

    async def test_upload_unsupported_file(self, client):
        response = await client.post(
            "/datasets",
            files={"file": ("readme.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 422

    async def test_upload_messy_csv(self, client):
        csv_path = FIXTURES_DIR / "sales_messy.csv"
        with open(csv_path, "rb") as f:
            response = await client.post(
                "/datasets",
                files={"file": ("sales_messy.csv", f, "text/csv")},
            )
        assert response.status_code == 201
        body = response.json()
        assert body["row_count"] == 10


class TestCRUD:
    async def _upload(self, client) -> str:
        csv_path = FIXTURES_DIR / "sales_simple.csv"
        with open(csv_path, "rb") as f:
            response = await client.post(
                "/datasets",
                files={"file": ("sales_simple.csv", f, "text/csv")},
            )
        return response.json()["id"]

    async def test_list_datasets(self, client):
        await self._upload(client)
        await self._upload(client)
        response = await client.get("/datasets")
        assert response.status_code == 200
        assert len(response.json()["datasets"]) >= 2

    async def test_get_dataset(self, client):
        dataset_id = await self._upload(client)
        response = await client.get(f"/datasets/{dataset_id}")
        assert response.status_code == 200
        assert response.json()["id"] == dataset_id

    async def test_get_nonexistent(self, client):
        response = await client.get("/datasets/ds_nonexistent")
        assert response.status_code == 404

    async def test_delete_dataset(self, client):
        dataset_id = await self._upload(client)
        response = await client.delete(f"/datasets/{dataset_id}")
        assert response.status_code == 204

        response = await client.get(f"/datasets/{dataset_id}")
        assert response.status_code == 404
