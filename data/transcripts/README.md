# Transcript data

Drop Lenny's Podcast transcripts here as plain `.txt` or `.md` files, one file
per episode. The filename (without extension) is used as the episode label
shown in citations, e.g. `ep-142-casey-winters-growth-loops.txt` becomes the
episode label `ep-142-casey-winters-growth-loops`.

## Where to get transcripts

Lenny's Podcast does not publish a bulk transcript API. Practical options:

1. **Manual export**: Lenny's newsletter posts include full transcripts for many
   episodes (lennysnewsletter.com) — copy/paste into a `.txt` file per episode.
2. **YouTube captions**: most episodes are on YouTube with auto-captions;
   download via `yt-dlp --write-auto-sub --skip-download <url>` and convert
   the `.vtt` to plain text.
3. **Podcast transcription service**: run episode audio through a
   transcription tool (e.g. Whisper) if you have the audio files.

This repo ships with 2 short SAMPLE transcripts (`sample-*.txt`) so the
ingestion pipeline and RAG flow can be demoed end-to-end without needing the
full corpus. Replace them with real transcripts for a production-quality demo.

## Running ingestion

```
cd backend
python -m app.ingestion.ingest_transcripts
```

This chunks every file here, embeds the chunks, and writes a FAISS index to
`FAISS_INDEX_DIR` (default `./data/faiss_index`). Re-run any time you add or
update transcripts — the index is fully rebuilt each run (see
`ingest_transcripts.py` docstring for why a full rebuild was chosen over
incremental updates at this corpus size).
