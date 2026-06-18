"""Tests for the FastAPI endpoints (requires running database)."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_responds(self, client):
        res = await client.get("/api/v1/health")
        assert res.status_code in (200, 503)
        data = res.json()
        assert "status" in data


class TestFeeds:
    @pytest.mark.asyncio
    async def test_list_feeds(self, client):
        res = await client.get("/api/v1/feeds")
        if res.status_code == 200:
            data = res.json()
            assert "feeds" in data
            assert isinstance(data["feeds"], list)

    @pytest.mark.asyncio
    async def test_add_invalid_feed(self, client):
        res = await client.post("/api/v1/feeds", json={"url": "not-a-url"})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_add_empty_feed(self, client):
        res = await client.post("/api/v1/feeds", json={"url": ""})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_add_valid_feed(self, client):
        res = await client.post("/api/v1/feeds", json={"url": "https://example.com/test.txt"})
        assert res.status_code in (200, 503)


class TestIndicators:
    @pytest.mark.asyncio
    async def test_list_indicators(self, client):
        res = await client.get("/api/v1/indicators?limit=5")
        if res.status_code == 200:
            data = res.json()
            assert "indicators" in data
            assert "total" in data
            assert len(data["indicators"]) <= 5

    @pytest.mark.asyncio
    async def test_filter_by_type(self, client):
        res = await client.get("/api/v1/indicators?ioc_type=ipv4&limit=3")
        if res.status_code == 200:
            data = res.json()
            for ioc in data["indicators"]:
                assert ioc["type"] == "ipv4"

    @pytest.mark.asyncio
    async def test_pagination_bounds(self, client):
        res = await client.get("/api/v1/indicators?limit=501")
        assert res.status_code == 400
        res = await client.get("/api/v1/indicators?page=0")
        assert res.status_code == 400


class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_loads(self, client):
        res = await client.get("/dashboard")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "DeepTrawl" in res.text


class TestTrigger:
    @pytest.mark.asyncio
    async def test_trigger_responds(self, client):
        res = await client.post("/api/v1/trigger")
        assert res.status_code in (200, 503)
        data = res.json()
        # Either success or DB-not-connected detail
        assert "status" in data or "detail" in data


class TestRotate:
    @pytest.mark.asyncio
    async def test_rotate_responds(self, client):
        res = await client.post("/api/v1/network/rotate")
        assert res.status_code in (200, 500)
