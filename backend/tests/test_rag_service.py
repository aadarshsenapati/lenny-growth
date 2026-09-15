from unittest.mock import patch

from app.agent.rag_service import format_context_block, retrieve


class FakeStore:
    def __init__(self, results):
        self._results = results

    def search(self, query, top_k):
        return self._results


@patch("app.agent.rag_service.get_vector_store")
def test_retrieve_flags_grounded_when_score_above_threshold(mock_get_store):
    mock_get_store.return_value = FakeStore(
        [{"chunk_id": "ep1::chunk-0", "episode": "ep1", "source": "ep1.txt", "text": "some text", "score": 0.6}]
    )
    chunks, grounded = retrieve("pricing strategy")
    assert grounded is True
    assert len(chunks) == 1


@patch("app.agent.rag_service.get_vector_store")
def test_retrieve_flags_not_grounded_when_all_scores_low(mock_get_store):
    mock_get_store.return_value = FakeStore(
        [{"chunk_id": "ep1::chunk-0", "episode": "ep1", "source": "ep1.txt", "text": "unrelated", "score": 0.05}]
    )
    chunks, grounded = retrieve("something totally unrelated to the corpus")
    assert grounded is False


def test_format_context_block_includes_source_and_episode():
    block = format_context_block(
        [{"chunk_id": "ep1::chunk-0", "episode": "ep1", "source": "ep1.txt", "text": "hello world", "score": 0.5}]
    )
    assert "ep1" in block
    assert "hello world" in block
