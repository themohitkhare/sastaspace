# tests/test_twenty_sync.py
"""Tests for Twenty CRM sync client. All HTTP calls mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

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
        client = NoopTwentyClient()
        result = await client.upsert_company("example.com", name="Test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_returns_noop_when_disabled(self):
        client = get_twenty_client(twenty_url="", twenty_api_key="")
        assert isinstance(client, NoopTwentyClient)

    @pytest.mark.asyncio
    async def test_get_client_returns_real_when_configured(self):
        client = get_twenty_client(twenty_url="http://twenty:3000/rest", twenty_api_key="key")
        assert isinstance(client, TwentyClient)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Connection refused")
            result = await client.upsert_company("example.com", name="Test")
            assert result is None
