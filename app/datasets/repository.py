"""Dataset repository — thin wrapper over MetadataStore for the service layer."""

from app.db.metadata import DatasetRecord, MetadataStore


class DatasetRepository:
    """Provides dataset CRUD operations to the service layer."""

    def __init__(self, store: MetadataStore) -> None:
        self._store = store

    async def save(self, record: DatasetRecord) -> None:
        """Persist a dataset record."""
        await self._store.save(record)

    async def get_by_id(self, dataset_id: str) -> DatasetRecord | None:
        """Retrieve a dataset by ID."""
        return await self._store.get_by_id(dataset_id)

    async def list_all(self) -> list[DatasetRecord]:
        """List all datasets."""
        return await self._store.list_all()

    async def delete_by_id(self, dataset_id: str) -> bool:
        """Delete a dataset by ID. Returns True if deleted."""
        return await self._store.delete_by_id(dataset_id)
