"""Tests for DuckDB manager and metadata store."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.db.duckdb import DuckDBManager
from app.db.metadata import DatasetRecord, MetadataStore

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SALES_CSV = str(FIXTURES_DIR / "sales_simple.csv")


@pytest.fixture
async def db():
    """Provide an in-memory DuckDB manager."""
    manager = DuckDBManager()
    await manager.startup(":memory:")
    yield manager
    await manager.shutdown()


@pytest.fixture
async def metadata_store(db):
    """Provide a metadata store with the table already created."""
    store = MetadataStore(db)
    await store.create_table()
    return store


class TestDuckDBManager:
    async def test_describe_table(self, db):
        rows = await db.describe_table(SALES_CSV)
        column_names = [r["column_name"] for r in rows]
        assert "fecha" in column_names
        assert "producto" in column_names
        assert "ventas" in column_names
        assert "sucursal" in column_names

    async def test_sample_rows(self, db):
        rows = await db.sample_rows(SALES_CSV, limit=3)
        assert len(rows) == 3
        assert "fecha" in rows[0]
        assert "ventas" in rows[0]

    async def test_count_rows(self, db):
        count = await db.count_rows(SALES_CSV)
        assert count == 20

    async def test_execute_query(self, db):
        sql = (
            f"SELECT sucursal, SUM(ventas) AS total FROM '{SALES_CSV}'"
            " GROUP BY sucursal ORDER BY total DESC"
        )
        result = await db.execute(sql)
        assert len(result) == 3
        assert result[0]["sucursal"] == "CDMX"


class TestMetadataStore:
    @staticmethod
    def _make_record(dataset_id: str = "ds_test001") -> DatasetRecord:
        return DatasetRecord(
            id=dataset_id,
            name="Test Dataset",
            table_name="test_dataset",
            file_path="/tmp/test.csv",
            schema_json=json.dumps([{"column": "a", "type": "INTEGER"}]),
            sample_json=json.dumps([{"a": 1}]),
            description="A test dataset",
            row_count=100,
            file_size_bytes=2048,
            created_at=datetime.now(),
        )

    async def test_save_and_get(self, metadata_store):
        record = self._make_record()
        await metadata_store.save(record)

        loaded = await metadata_store.get_by_id("ds_test001")
        assert loaded is not None
        assert loaded.name == "Test Dataset"
        assert loaded.table_name == "test_dataset"
        assert loaded.row_count == 100

    async def test_get_nonexistent(self, metadata_store):
        result = await metadata_store.get_by_id("ds_nonexistent")
        assert result is None

    async def test_list_all(self, metadata_store):
        await metadata_store.save(self._make_record("ds_001"))
        await metadata_store.save(self._make_record("ds_002"))

        all_records = await metadata_store.list_all()
        assert len(all_records) == 2

    async def test_delete(self, metadata_store):
        await metadata_store.save(self._make_record("ds_del"))

        deleted = await metadata_store.delete_by_id("ds_del")
        assert deleted is True

        result = await metadata_store.get_by_id("ds_del")
        assert result is None

    async def test_delete_nonexistent(self, metadata_store):
        deleted = await metadata_store.delete_by_id("ds_nope")
        assert deleted is False
