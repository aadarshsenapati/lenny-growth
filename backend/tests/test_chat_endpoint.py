from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.llm_provider import LLMResult
from app.db.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def sqlite_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


def _fake_llm_result(text="Mocked grounded answer.", provider="groq"):
    return LLMResult(text=text, provider=provider, model="mock-model", latency_ms=42)


@pytest.mark.asyncio
@patch("app.agent.rag_service.get_vector_store")
async def test_chat_grounded_qa_persists_and_returns_citations(mock_store, sqlite_client):
    mock_store.return_value.search.return_value = [
        {"chunk_id": "ep1::chunk-0", "episode": "ep1", "source": "ep1.txt", "text": "pricing advice", "score": 0.55}
    ]

    session = (await sqlite_client.post("/sessions", json={"user_id": "alice"})).json()

    with patch("app.api.routes_chat.get_llm_client") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = _fake_llm_result()
        mock_get_llm.return_value = mock_llm

        resp = await sqlite_client.post(
            "/chat", json={"session_id": session["id"], "message": "What do guests say about pricing?"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["skill_used"] == "grounded_qa"
    assert body["grounded"] is True
    assert len(body["citations"]) == 1
    assert body["citations"][0]["episode"] == "ep1"
    assert body["content"] == "Mocked grounded answer."

    # Persistence: both user and assistant turns are stored.
    messages = (await sqlite_client.get(f"/sessions/{session['id']}/messages")).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["skill_used"] == "grounded_qa"

    # First message auto-titles the session.
    updated_session = (await sqlite_client.get(f"/sessions/{session['id']}")).json()
    assert updated_session["title"] == "What do guests say about pricing?"


@pytest.mark.asyncio
@patch("app.agent.rag_service.get_vector_store")
async def test_chat_ship30_trigger_routes_to_ship30_skill(mock_store, sqlite_client):
    mock_store.return_value.search.return_value = []
    session = (await sqlite_client.post("/sessions", json={"user_id": "alice"})).json()

    with patch("app.api.routes_chat.get_llm_client") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = _fake_llm_result(text="# Essay Title\n\nBody...")
        mock_get_llm.return_value = mock_llm

        resp = await sqlite_client.post(
            "/chat",
            json={"session_id": session["id"], "message": "Turn this into a Ship 30 for 30 essay"},
        )

    assert resp.status_code == 200
    assert resp.json()["skill_used"] == "ship30"


@pytest.mark.asyncio
@patch("app.agent.rag_service.get_vector_store")
async def test_chat_artifact_trigger_creates_persisted_artifact(mock_store, sqlite_client):
    mock_store.return_value.search.return_value = []
    session = (await sqlite_client.post("/sessions", json={"user_id": "alice"})).json()

    with patch("app.api.routes_chat.get_llm_client") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = _fake_llm_result(text="# Summary\n\n- point one\n- point two")
        mock_get_llm.return_value = mock_llm

        resp = await sqlite_client.post(
            "/chat",
            json={"session_id": session["id"], "message": "Generate a markdown document summarizing this"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["skill_used"] == "artifact"
    assert body["artifact"] is not None
    assert body["artifact"]["kind"] == "markdown"

    artifacts = (await sqlite_client.get(f"/artifacts/session/{session['id']}")).json()
    assert len(artifacts) == 1
    assert artifacts[0]["content"].startswith("# Summary")


@pytest.mark.asyncio
async def test_chat_with_unknown_session_returns_404(sqlite_client):
    resp = await sqlite_client.post(
        "/chat", json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hello"}
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "session_not_found"


@pytest.mark.asyncio
@patch("app.agent.rag_service.get_vector_store")
async def test_chat_llm_unavailable_returns_typed_error(mock_store, sqlite_client):
    from app.core.exceptions import LLMProviderUnavailableError

    mock_store.return_value.search.return_value = []
    session = (await sqlite_client.post("/sessions", json={"user_id": "alice"})).json()

    with patch("app.api.routes_chat.get_llm_client") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = LLMProviderUnavailableError("Ollama is not reachable.")
        mock_get_llm.return_value = mock_llm

        resp = await sqlite_client.post(
            "/chat", json={"session_id": session["id"], "message": "hello", "llm_provider": "ollama"}
        )

    assert resp.status_code == 503
    assert resp.json()["code"] == "llm_provider_unavailable"

    # The user's message should still be persisted even though the LLM call failed.
    messages = (await sqlite_client.get(f"/sessions/{session['id']}/messages")).json()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
