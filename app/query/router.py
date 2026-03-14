"""HTTP endpoint for querying datasets."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.datasets.repository import DatasetRepository
from app.db.duckdb import DuckDBManager
from app.db.metadata import MetadataStore
from app.dependencies import get_db, get_llm_client, get_metadata_store, get_settings
from app.llm.base import LLMClient
from app.query.schemas import QueryRequest, QueryResponse
from app.query.service import QueryService

router = APIRouter(tags=["query"])


def _get_query_service(
    db: Annotated[DuckDBManager, Depends(get_db)],
    store: Annotated[MetadataStore, Depends(get_metadata_store)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryService:
    """Build a QueryService with injected dependencies."""
    return QueryService(
        db=db,
        repository=DatasetRepository(store),
        llm_client=llm_client,
        row_limit=settings.QUERY_RESULT_LIMIT,
    )


QueryServiceDep = Annotated[QueryService, Depends(_get_query_service)]


@router.post(
    "/datasets/{dataset_id}/query",
    response_model=QueryResponse,
)
async def query_dataset(
    dataset_id: str,
    request: QueryRequest,
    service: QueryServiceDep,
) -> QueryResponse:
    """Query a dataset using natural language."""
    return await service.run_query(dataset_id, request)
