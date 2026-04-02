"""端到端 API 测试"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "super-agent"


@pytest.mark.asyncio
async def test_gateway_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_submit_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/query",
            json={"query": "查找近三个月AI专利趋势"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
        assert "trace_id" in data


@pytest.mark.asyncio
async def test_submit_query_with_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/query",
            json={
                "query": "对比专利数据",
                "session_id": "test-session-001",
                "mode": "plan_and_execute",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-001"


@pytest.mark.asyncio
async def test_submit_query_empty_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/query",
            json={"query": ""},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_swagger_docs_available():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200
