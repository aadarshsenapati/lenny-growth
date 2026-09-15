"""Retrieval layer shared by every skill. Keeps the "grounding" contract in
one place: given a query, return the top transcript chunks plus a boolean
signal for whether the material actually supports an answer."""
from app.config import get_settings
from app.ingestion.faiss_store import get_vector_store
from app.logging_config import get_logger

log = get_logger(__name__)


def retrieve(query: str, top_k: int | None = None) -> tuple[list[dict], bool]:
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    store = get_vector_store()
    results = store.search(query, top_k=k)
    grounded = any(r["score"] >= settings.min_similarity_score for r in results)
    if not grounded:
        log.info("retrieval_below_threshold", query=query[:120], top_score=results[0]["score"] if results else None)
    return results, grounded


def format_context_block(chunks: list[dict]) -> str:
    """Turns retrieved chunks into a citable context block for the prompt."""
    lines = []
    for c in chunks:
        lines.append(f"[Source: {c['episode']} | chunk: {c['chunk_id']} | score: {c['score']:.2f}]\n{c['text']}")
    return "\n\n---\n\n".join(lines)
