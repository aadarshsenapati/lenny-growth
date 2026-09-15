"""
Ingestion entrypoint.

Usage:
    python -m app.ingestion.ingest_transcripts

Expects transcript files under ../data/transcripts/ as plain .txt or .md
files. Each file is treated as one episode; the filename (minus extension)
becomes the episode label, and the file path is stored as `source` so every
retrieved chunk can be traced back to exactly where it came from.

Refreshing: re-running this script re-embeds ALL transcripts and overwrites
the FAISS index. For the corpus size involved (a few hundred episodes) a
full rebuild is simpler and more reliable than incremental updates, and
takes well under a minute on CPU. If the corpus grows much larger, switch to
incremental upsert-by-chunk-id.
"""
import sys
from pathlib import Path

from app.ingestion.chunker import chunk_text
from app.ingestion.faiss_store import build_index
from app.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

TRANSCRIPT_DIR = Path(__file__).resolve().parents[3] / "data" / "transcripts"


def load_transcripts() -> list[dict]:
    files = sorted(list(TRANSCRIPT_DIR.glob("*.txt")) + list(TRANSCRIPT_DIR.glob("*.md")))
    if not files:
        log.error("no_transcripts_found", dir=str(TRANSCRIPT_DIR))
        return []
    all_chunks = []
    for path in files:
        episode = path.stem
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            log.warning("empty_transcript_skipped", file=str(path))
            continue
        chunks = chunk_text(text, episode=episode, source=str(path.relative_to(TRANSCRIPT_DIR.parents[0])))
        all_chunks.extend(chunks)
        log.info("transcript_chunked", episode=episode, num_chunks=len(chunks))
    return all_chunks


def main() -> int:
    chunks = load_transcripts()
    if not chunks:
        log.error("ingestion_aborted_no_data")
        print(
            f"No transcripts found in {TRANSCRIPT_DIR}. "
            "Add .txt/.md transcript files (see data/transcripts/README.md) and re-run."
        )
        return 1
    build_index(chunks)
    print(f"Indexed {len(chunks)} chunks from {TRANSCRIPT_DIR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
