# tests/test_twenty_sync.py
"""Tests for Twenty CRM sync client. All HTTP calls mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sastaspace.twenty_sync import NoopTwentyClient, TwentyClient, get_twenty_client


@pytest.fixture
def client():
    return TwentyClient(base_url="http://twenty:3000/rest", api_key="test-key")


class TestUpsertCompany:
    @pytest.mark.asyncio
    async def test_creates_company_when_not_found(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            # find_company_by_domain tries 3 URL variants + 1 name fallback, all empty
            # then upsert_company creates
            empty = {"data": {"companies": []}}
            mock_req.side_effect = [
                empty,
                empty,
                empty,
                empty,  # 3 URL variants + name fallback
                {"data": {"createCompany": {"id": "c1"}}},  # create
            ]
            result = await client.upsert_company("example.com", name="Example Corp")
            assert result["id"] == "c1"

    @pytest.mark.asyncio
    async def test_updates_company_when_found(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            # First URL variant search finds the company
            mock_req.side_effect = [
                {"data": {"companies": [{"id": "c1"}]}},  # found on first variant
                {"data": {"updateCompany": {"id": "c1"}}},  # update
            ]
            result = await client.upsert_company("example.com", name="Example Corp Updated")
            assert result["id"] == "c1"


class TestCreatePerson:
    @pytest.mark.asyncio
    async def test_creates_person_linked_to_company(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"createPerson": {"id": "p1"}}}
            result = await client.create_person(
                email="test@example.com",
                company_id="c1",
                first_name="John",
                last_name="Doe",
            )
            assert result["id"] == "p1"

    @pytest.mark.asyncio
    async def test_creates_person_without_company(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"createPerson": {"id": "p2"}}}
            result = await client.create_person(
                email="test@example.com",
                company_id=None,
                first_name="Jane",
                last_name="Doe",
            )
            assert result["id"] == "p2"


class TestFeatureFlag:
    @pytest.mark.asyncio
    async def test_noop_client_does_nothing(self):
        noop = NoopTwentyClient()
        result = await noop.upsert_company("example.com", name="Test")
        assert result is None

    @pytest.mark.asyncio
    async def test_noop_client_health_check_returns_true(self):
        noop = NoopTwentyClient()
        assert await noop.health_check() is True

    @pytest.mark.asyncio
    async def test_get_client_returns_noop_when_disabled(self):
        result = get_twenty_client(twenty_url="", twenty_api_key="")
        assert isinstance(result, NoopTwentyClient)

    @pytest.mark.asyncio
    async def test_get_client_returns_real_when_configured(self):
        result = get_twenty_client(twenty_url="http://twenty:3000/rest", twenty_api_key="key")
        assert isinstance(result, TwentyClient)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Connection refused")
            result = await client.upsert_company("example.com", name="Test")
            assert result is None

    @pytest.mark.asyncio
    async def test_timeout_in_find_company_returns_none(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.ReadTimeout("read timed out")
            result = await client.find_company_by_domain("example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_timeout_in_create_person_returns_none(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.ConnectTimeout("connect timed out")
            result = await client.create_person(
                email="a@b.com", company_id="c1", first_name="A", last_name="B"
            )
            assert result is None


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_passes(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"companies": []}}
            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_fails_on_timeout(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.ReadTimeout("timed out")
            assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_fails_on_auth_error(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            resp = httpx.Response(
                401, text="Unauthorized", request=httpx.Request("GET", "http://x")
            )
            mock_req.side_effect = httpx.HTTPStatusError("401", request=resp.request, response=resp)
            assert await client.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_fails_on_connection_error(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.ConnectError("Connection refused")
            assert await client.health_check() is False


class TestRetry:
    @pytest.mark.asyncio
    async def test_request_retries_on_timeout(self, client):
        """_request retries once on timeout, succeeds on second attempt."""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ReadTimeout("timed out")
            req = httpx.Request("GET", "http://twenty:3000/rest/companies")
            return httpx.Response(200, json={"data": {"companies": []}}, request=req)

        with patch("httpx.AsyncClient.request", side_effect=mock_request):
            result = await client._request("GET", "/companies")
            assert result == {"data": {"companies": []}}
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_request_raises_after_max_retries(self, client):
        """_request raises after exhausting retries on persistent timeout."""

        async def mock_request(*args, **kwargs):
            raise httpx.ReadTimeout("timed out")

        with patch("httpx.AsyncClient.request", side_effect=mock_request):
            with pytest.raises(httpx.ReadTimeout):
                await client._request("GET", "/companies")
