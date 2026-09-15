import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_status(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded", "down")
    assert "database" in body
    assert "faiss_index_loaded" in body
    assert "llm_provider" in body
