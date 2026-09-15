"""
FAISS vector store for transcript chunks.

Design notes:
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (small, fast, CPU-only,
  no API cost -- keeps ingestion free and local-model-friendly).
- Index type: IndexFlatIP over L2-normalized vectors == cosine similarity.
  Flat is intentional: the Lenny transcript corpus is small enough (tens of
  thousands of chunks at most) that an exact-search flat index is fast
  enough and avoids ANN tuning/quality trade-offs.
- Persistence: index + a parallel metadata JSON are written to
  FAISS_INDEX_DIR. Both are loaded at startup; if missing, retrieval
  degrades gracefully (RetrievalIndexMissingError) instead of crashing.
"""
import json
from pathlib import Path

import faiss
import numpy as np

from app.config import get_settings
from app.core.exceptions import RetrievalIndexMissingError
from app.logging_config import get_logger

log = get_logger(__name__)

_model_cache = None


def _get_embedder():
    """Lazy import: keeps the embedding model (and its torch dependency) out
    of the import path for code that never needs it (e.g. session routes,
    health checks when the index isn't loaded yet), and lets /health report
    a clean error instead of an ImportError crash if the ML deps are missing."""
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        _model_cache = SentenceTransformer(settings.embedding_model)
    return _model_cache


def _embed(texts: list[str]) -> np.ndarray:
    embedder = _get_embedder()
    vecs = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype="float32")


def build_index(chunks: list[dict]) -> None:
    """Embeds all chunks and writes a fresh FAISS index + metadata to disk.
    Re-run this whenever transcripts are added/refreshed (see
    ingest_transcripts.py)."""
    settings = get_settings()
    out_dir = Path(settings.faiss_index_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    texts = [c["text"] for c in chunks]
    vectors = _embed(texts)
    dim = vectors.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    faiss.write_index(index, str(out_dir / "index.faiss"))
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(chunks, f)

    log.info("faiss_index_built", num_chunks=len(chunks), dim=dim)


class VectorStore:
    def __init__(self):
        self.index: faiss.Index | None = None
        self.metadata: list[dict] = []
        self._load()

    def _load(self) -> None:
        settings = get_settings()
        index_path = Path(settings.faiss_index_dir) / "index.faiss"
        meta_path = Path(settings.faiss_index_dir) / "metadata.json"
        if not index_path.exists() or not meta_path.exists():
            log.warning("faiss_index_missing", path=str(index_path))
            self.index = None
            self.metadata = []
            return
        self.index = faiss.read_index(str(index_path))
        with open(meta_path) as f:
            self.metadata = json.load(f)

    @property
    def is_loaded(self) -> bool:
        return self.index is not None and len(self.metadata) > 0

    def search(self, query: str, top_k: int) -> list[dict]:
        if not self.is_loaded:
            raise RetrievalIndexMissingError(
                "No transcript index found. Run `python -m app.ingestion.ingest_transcripts` first."
            )
        q_vec = _embed([query])
        scores, ids = self.index.search(q_vec, top_k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            results.append({**meta, "score": float(score)})
        return results


_store_singleton: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = VectorStore()
    return _store_singleton


def reload_vector_store() -> VectorStore:
    """Call after re-ingesting so a running server picks up the new index
    without a restart."""
    global _store_singleton
    _store_singleton = VectorStore()
    return _store_singleton
