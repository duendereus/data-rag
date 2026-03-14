"""HTTP endpoints for dataset management."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config import Settings
from app.datasets.repository import DatasetRepository
from app.datasets.schemas import DatasetListResponse, DatasetResponse
from app.datasets.service import DatasetService
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.dependencies import get_db, get_metadata_store, get_settings

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _get_service(
    db: Annotated[DuckDBManager, Depends(get_db)],
    store: Annotated[MetadataStore, Depends(get_metadata_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DatasetService:
    """Build a DatasetService with injected dependencies."""
    return DatasetService(db=db, repository=DatasetRepository(store), settings=settings)


ServiceDep = Annotated[DatasetService, Depends(_get_service)]


@router.post("", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    service: ServiceDep,
    file: Annotated[UploadFile, File(...)],
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
) -> DatasetResponse:
    """Upload a CSV or Excel file and extract its schema."""
    return await service.upload(file, name=name, description=description)


@router.get("", response_model=DatasetListResponse)
async def list_datasets(service: ServiceDep) -> DatasetListResponse:
    """List all uploaded datasets."""
    datasets = await service.list_datasets()
    return DatasetListResponse(datasets=datasets)


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str, service: ServiceDep) -> DatasetResponse:
    """Get metadata for a specific dataset."""
    return await service.get_dataset(dataset_id)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, service: ServiceDep) -> None:
    """Delete a dataset and its associated file."""
    await service.delete_dataset(dataset_id)
