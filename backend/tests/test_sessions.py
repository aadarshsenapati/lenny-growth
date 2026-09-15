import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def sqlite_client():
    """Isolated in-memory SQLite DB per test so session/message persistence
    logic is verified without requiring a live MySQL instance."""
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


@pytest.mark.asyncio
async def test_create_session_persists_and_is_independent(sqlite_client):
    resp1 = await sqlite_client.post("/sessions", json={"user_id": "alice"})
    resp2 = await sqlite_client.post("/sessions", json={"user_id": "alice"})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    id1, id2 = resp1.json()["id"], resp2.json()["id"]
    assert id1 != id2  # independent session contexts


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_404(sqlite_client):
    resp = await sqlite_client.get("/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "session_not_found"


@pytest.mark.asyncio
async def test_list_sessions_scoped_to_user(sqlite_client):
    await sqlite_client.post("/sessions", json={"user_id": "alice"})
    await sqlite_client.post("/sessions", json={"user_id": "bob"})

    alice_sessions = (await sqlite_client.get("/sessions", params={"user_id": "alice"})).json()
    bob_sessions = (await sqlite_client.get("/sessions", params={"user_id": "bob"})).json()

    assert len(alice_sessions) == 1
    assert len(bob_sessions) == 1
    assert alice_sessions[0]["id"] != bob_sessions[0]["id"]


@pytest.mark.asyncio
async def test_delete_session_removes_it(sqlite_client):
    created = (await sqlite_client.post("/sessions", json={"user_id": "alice"})).json()
    del_resp = await sqlite_client.delete(f"/sessions/{created['id']}")
    assert del_resp.status_code == 204
    get_resp = await sqlite_client.get(f"/sessions/{created['id']}")
    assert get_resp.status_code == 404
