from fastapi import APIRouter

from app.agent.llm_provider import OllamaClient, get_llm_client
from app.config import get_settings
from app.db.database import check_db_connection
from app.db.schemas import HealthResponse
from app.ingestion.faiss_store import get_vector_store

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    db_ok = await check_db_connection()
    store = get_vector_store()
    llm = get_llm_client()
    llm_ok = await llm.is_reachable()
    ollama_ok = await OllamaClient().is_reachable()

    status = "ok"
    if not db_ok or not store.is_loaded or not llm_ok:
        status = "degraded"
    if not db_ok and not store.is_loaded:
        status = "down"

    return HealthResponse(
        status=status,
        database=db_ok,
        faiss_index_loaded=store.is_loaded,
        llm_provider=settings.llm_provider,
        llm_reachable=llm_ok,
        ollama_available=ollama_ok,
    )
