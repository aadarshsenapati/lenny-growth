from app.ingestion.chunker import chunk_text


def test_chunk_text_produces_traceable_chunks():
    text = "word " * 1000
    chunks = chunk_text(text, episode="ep-42-example", source="data/transcripts/ep-42-example.txt")
    assert len(chunks) > 1
    for i, c in enumerate(chunks):
        assert c["episode"] == "ep-42-example"
        assert c["chunk_id"] == f"ep-42-example::chunk-{i}"
        assert c["source"].endswith("ep-42-example.txt")
        assert len(c["text"]) > 0


def test_chunk_text_handles_short_input():
    chunks = chunk_text("Just one short sentence.", episode="ep-1", source="ep-1.txt")
    assert len(chunks) == 1
