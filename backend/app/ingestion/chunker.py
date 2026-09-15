"""Splits transcripts into overlapping, token-bounded chunks so each chunk
fits comfortably in a retrieval context window and traces back to its
source episode."""
import tiktoken

from app.config import get_settings

_enc = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, episode: str, source: str) -> list[dict]:
    settings = get_settings()
    tokens = _enc.encode(text)
    size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens

    chunks = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_str = _enc.decode(chunk_tokens)
        chunks.append(
            {
                "chunk_id": f"{episode}::chunk-{idx}",
                "text": chunk_str,
                "episode": episode,
                "source": source,
            }
        )
        idx += 1
        if end == len(tokens):
            break
        start = end - overlap
    return chunks
