# sastaspace/twenty_sync.py
"""Twenty CRM sync client — async wrapper around Twenty REST API."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TwentyClient:
    """Async client for Twenty CRM REST API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _request(
        self, method: str, path: str, json: dict | None = None, params: dict | None = None
    ) -> dict:
        """Make an authenticated request to Twenty API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def find_company_by_domain(self, domain: str) -> dict | None:
        """Find a company by custom domain field."""
        try:
            data = await self._request(
                "GET",
                "/companies",
                params={"filter": f'{{"domain":{{"eq":"{domain}"}}}}'},
            )
            companies = data.get("data", {}).get("companies", [])
            return companies[0] if companies else None
        except Exception as e:
            logger.warning("Twenty find_company failed: %s", e)
            return None

    async def upsert_company(self, domain: str, **fields) -> dict | None:
        """Find company by domain, update if exists, create if not."""
        try:
            existing = await self.find_company_by_domain(domain)
            if existing:
                data = await self._request("PATCH", f"/companies/{existing['id']}", json=fields)
                return data.get("data", {}).get("updateCompany", existing)
            else:
                fields["domain"] = domain
                data = await self._request("POST", "/companies", json=fields)
                return data.get("data", {}).get("createCompany")
        except Exception as e:
            logger.warning("Twenty upsert_company failed for %s: %s", domain, e)
            return None

    async def create_redesign_job(self, company_id: str, **fields) -> dict | None:
        """Create a RedesignJob record linked to a company."""
        try:
            fields["companyId"] = company_id
            data = await self._request("POST", "/redesignJobs", json=fields)
            return data.get("data", {}).get("createRedesignJob")
        except Exception as e:
            logger.warning("Twenty create_redesign_job failed: %s", e)
            return None

    async def update_redesign_job(self, record_id: str, **fields) -> dict | None:
        """Update fields on an existing RedesignJob."""
        try:
            data = await self._request("PATCH", f"/redesignJobs/{record_id}", json=fields)
            return data.get("data", {}).get("updateRedesignJob")
        except Exception as e:
            logger.warning("Twenty update_redesign_job failed: %s", e)
            return None

    async def find_redesign_job(self, job_id: str) -> dict | None:
        """Find a RedesignJob by SastaSpace job ID."""
        try:
            data = await self._request(
                "GET",
                "/redesignJobs",
                params={"filter": f'{{"jobId":{{"eq":"{job_id}"}}}}'},
            )
            jobs = data.get("data", {}).get("redesignJobs", [])
            return jobs[0] if jobs else None
        except Exception as e:
            logger.warning("Twenty find_redesign_job failed: %s", e)
            return None

    async def create_person(
        self, email: str, company_id: str | None, first_name: str, last_name: str, **fields
    ) -> dict | None:
        """Create a Person record, optionally linked to a company."""
        try:
            body = {"email": email, "firstName": first_name, "lastName": last_name, **fields}
            if company_id:
                body["companyId"] = company_id
            data = await self._request("POST", "/people", json=body)
            return data.get("data", {}).get("createPerson")
        except Exception as e:
            logger.warning("Twenty create_person failed: %s", e)
            return None

    async def create_note(self, person_id: str, body: str) -> dict | None:
        """Create a Note linked to a person."""
        try:
            data = await self._request("POST", "/notes", json={"body": body, "personId": person_id})
            return data.get("data", {}).get("createNote")
        except Exception as e:
            logger.warning("Twenty create_note failed: %s", e)
            return None


class NoopTwentyClient:
    """No-op client used when Twenty integration is disabled."""

    async def upsert_company(self, *a, **kw):
        return None

    async def create_redesign_job(self, *a, **kw):
        return None

    async def update_redesign_job(self, *a, **kw):
        return None

    async def find_redesign_job(self, *a, **kw):
        return None

    async def find_company_by_domain(self, *a, **kw):
        return None

    async def create_person(self, *a, **kw):
        return None

    async def create_note(self, *a, **kw):
        return None


def get_twenty_client(twenty_url: str, twenty_api_key: str) -> TwentyClient | NoopTwentyClient:
    """Factory — returns NoopTwentyClient when twenty_url is empty."""
    if not twenty_url:
        return NoopTwentyClient()
    return TwentyClient(base_url=twenty_url, api_key=twenty_api_key)
