# tests/test_twenty_integration.py
"""Integration tests for Twenty CRM sync flow. All HTTP calls mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.twenty_sync import NoopTwentyClient, TwentyClient, get_twenty_client


@pytest.fixture
def client():
    return TwentyClient(base_url="http://twenty:3000/rest", api_key="test-key")


# --- Multi-step flow tests ---


class TestJobCompletionFlow:
    @pytest.mark.asyncio
    async def test_job_completion_creates_company_and_job(self, client):
        """Simulate full flow: upsert_company (search empty → create) then create_redesign_job."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                # upsert_company: search returns empty
                {"data": {"companies": []}},
                # upsert_company: create returns new company
                {"data": {"createCompany": {"id": "comp-1", "domain": "example.com"}}},
                # create_redesign_job: returns new job
                {"data": {"createRedesignJob": {"id": "rj-1", "companyId": "comp-1"}}},
            ]

            company = await client.upsert_company("example.com", name="Example Corp")
            assert company is not None
            assert company["id"] == "comp-1"

            job = await client.create_redesign_job(
                company_id=company["id"], job_id="j-abc", status="done", tier="free"
            )
            assert job is not None
            assert job["id"] == "rj-1"
            assert mock_req.call_count == 3


class TestContactFormFlow:
    @pytest.mark.asyncio
    async def test_contact_form_creates_person_with_note(self, client):
        """Simulate contact form: find_company → create_person → create_note."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                # find_company_by_domain: returns existing company
                {
                    "data": {
                        "companies": [{"id": "comp-1", "domain": "example.com"}],
                    }
                },
                # create_person: returns new person linked to company
                {"data": {"createPerson": {"id": "p-1", "companyId": "comp-1"}}},
                # create_note: returns new note linked to person
                {"data": {"createNote": {"id": "n-1", "personId": "p-1"}}},
            ]

            company = await client.find_company_by_domain("example.com")
            assert company is not None
            company_id = company["id"]

            person = await client.create_person(
                email="john@example.com",
                company_id=company_id,
                first_name="John",
                last_name="Doe",
            )
            assert person is not None
            assert person["id"] == "p-1"

            note = await client.create_note(
                person_id=person["id"],
                body="Interested in redesign services.",
            )
            assert note is not None
            assert note["id"] == "n-1"
            assert mock_req.call_count == 3


# --- NoopTwentyClient safety ---


class TestNoopClientSafety:
    @pytest.mark.asyncio
    async def test_noop_client_safe_for_all_operations(self):
        """Every method on NoopTwentyClient returns None without errors."""
        noop = NoopTwentyClient()

        assert await noop.upsert_company("example.com", name="Test") is None
        assert await noop.create_redesign_job("c1", job_id="j1") is None
        assert await noop.update_redesign_job("rj1", status="done") is None
        assert await noop.find_redesign_job("j1") is None
        assert await noop.find_company_by_domain("example.com") is None
        assert await noop.create_person("a@b.com", None, "A", "B") is None
        assert await noop.create_note("p1", "hello") is None


# --- Factory function ---


class TestGetClientFactory:
    def test_get_client_returns_noop_when_disabled(self):
        """Empty URL → NoopTwentyClient."""
        result = get_twenty_client("", "")
        assert isinstance(result, NoopTwentyClient)

    def test_get_client_returns_real_when_configured(self):
        """Non-empty URL → TwentyClient."""
        result = get_twenty_client("http://twenty:3000/rest", "key")
        assert isinstance(result, TwentyClient)
