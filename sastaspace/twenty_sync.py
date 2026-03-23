# sastaspace/twenty_sync.py
"""Twenty CRM sync client — async wrapper around Twenty REST API."""

from __future__ import annotations

import logging

import httpx

from sastaspace.twenty_models import (
    CompanyCreateRequest,
    CompanyUpdateRequest,
    NoteCreateRequest,
    NoteTargetCreateRequest,
    PersonCreateRequest,
    TwentyDomainName,
    TwentyEmails,
    TwentyNoteBody,
    TwentyPersonName,
)

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
        """Find a company by domainName.primaryLinkUrl."""
        try:
            url_variants = [f"https://{domain}", f"http://{domain}", domain]
            for variant in url_variants:
                data = await self._request(
                    "GET",
                    "/companies",
                    params={"filter": f"domainName.primaryLinkUrl[eq]:{variant}"},
                )
                companies = data.get("data", {}).get("companies", [])
                if companies:
                    return companies[0]
            # Also try name-based search as fallback
            data = await self._request(
                "GET",
                "/companies",
                params={"filter": f"name[like]:%{domain}%"},
            )
            companies = data.get("data", {}).get("companies", [])
            return companies[0] if companies else None
        except Exception as e:
            logger.warning("Twenty find_company failed: %s", e)
            return None

    async def upsert_company(self, domain: str, name: str | None = None) -> dict | None:
        """Find company by domain, update if exists, create if not."""
        try:
            existing = await self.find_company_by_domain(domain)
            if existing:
                if name:
                    body = CompanyUpdateRequest(name=name)
                    data = await self._request(
                        "PATCH",
                        f"/companies/{existing['id']}",
                        json=body.model_dump(exclude_none=True),
                    )
                    return data.get("data", {}).get("updateCompany", existing)
                return existing
            else:
                body = CompanyCreateRequest(
                    name=name or domain,
                    domainName=TwentyDomainName(primaryLinkUrl=f"https://{domain}"),
                )
                data = await self._request("POST", "/companies", json=body.model_dump())
                return data.get("data", {}).get("createCompany")
        except Exception as e:
            logger.warning("Twenty upsert_company failed for %s: %s", domain, e)
            return None

    async def create_person(
        self, email: str, company_id: str | None, first_name: str, last_name: str
    ) -> dict | None:
        """Create a Person record, optionally linked to a company."""
        try:
            body = PersonCreateRequest(
                name=TwentyPersonName(firstName=first_name, lastName=last_name),
                emails=TwentyEmails(primaryEmail=email),
                companyId=company_id,
            )
            data = await self._request("POST", "/people", json=body.model_dump(exclude_none=True))
            return data.get("data", {}).get("createPerson")
        except Exception as e:
            logger.warning("Twenty create_person failed: %s", e)
            return None

    async def create_note(self, person_id: str, body: str) -> dict | None:
        """Create a Note and attempt to link it to a person."""
        try:
            note_body = NoteCreateRequest(
                title="Contact form message",
                bodyV2=TwentyNoteBody(markdown=body),
            )
            note_data = await self._request("POST", "/notes", json=note_body.model_dump())
            note = note_data.get("data", {}).get("createNote")
            if not note:
                return None
            # Try to link note to person (best-effort)
            try:
                link = NoteTargetCreateRequest(
                    noteId=note["id"],
                    targetObjectNameSingular="person",
                    targetObjectRecordId=person_id,
                )
                await self._request("POST", "/noteTargets", json=link.model_dump())
            except Exception as e:
                logger.warning("Twenty noteTarget link failed (note still created): %s", e)
            return note
        except Exception as e:
            logger.warning("Twenty create_note failed: %s", e)
            return None


class NoopTwentyClient:
    """No-op client used when Twenty integration is disabled."""

    async def upsert_company(self, *a, **kw):
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
