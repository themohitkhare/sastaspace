# sastaspace/twenty_sync.py
# DEPRECATED: Use espocrm_sync.py instead. This file will be removed
# once EspoCRM migration is verified in production.
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

# Default timeout for all Twenty API calls (connect, read, write, pool)
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Number of retries on transient errors (timeouts, 502/503/504)
_MAX_RETRIES = 1

_RETRYABLE_STATUS_CODES = {502, 503, 504}


class TwentyClient:
    """Async client for Twenty CRM REST API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _request(
        self, method: str, path: str, json: dict | None = None, params: dict | None = None
    ) -> dict:
        """Make an authenticated request to Twenty API with retry on transient errors."""
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                    resp = await client.request(
                        method,
                        url,
                        json=json,
                        params=params,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                    if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                        logger.warning(
                            "Twenty API %s %s returned %s (attempt %d/%d), retrying",
                            method,
                            path,
                            resp.status_code,
                            attempt + 1,
                            _MAX_RETRIES + 1,
                        )
                        continue
                    if resp.status_code >= 400:
                        logger.error(
                            "Twenty API error: %s %s → %s body=%s",
                            method,
                            path,
                            resp.status_code,
                            resp.text[:500],
                        )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Twenty API timeout: %s %s (attempt %d/%d), retrying",
                        method,
                        path,
                        attempt + 1,
                        _MAX_RETRIES + 1,
                    )
                    continue
                logger.error(
                    "Twenty API timeout after %d attempts: %s %s",
                    attempt + 1,
                    method,
                    path,
                )
                raise
            except httpx.HTTPStatusError:
                # Already logged above before raise_for_status
                raise
            except httpx.HTTPError as e:
                last_exc = e
                logger.error(
                    "Twenty API HTTP error: %s %s → %s: %s",
                    method,
                    path,
                    type(e).__name__,
                    e,
                )
                raise

        # Should not reach here, but satisfy type checker
        raise last_exc  # type: ignore[misc]

    async def health_check(self) -> bool:
        """Verify Twenty API is reachable and the API key is valid.

        Returns True if the API responds, False otherwise. Logs the outcome.
        """
        try:
            await self._request("GET", "/companies", params={"limit": "1"})
            logger.info("Twenty CRM health check passed (%s)", self.base_url)
            return True
        except httpx.TimeoutException:
            logger.error("Twenty CRM health check failed: timeout connecting to %s", self.base_url)
            return False
        except httpx.HTTPStatusError as e:
            logger.error(
                "Twenty CRM health check failed: %s %s (is API key valid?)",
                e.response.status_code,
                e.response.text[:200],
            )
            return False
        except Exception as e:
            logger.error("Twenty CRM health check failed: %s: %s", type(e).__name__, e)
            return False

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
            logger.warning(
                "Twenty find_company failed for domain=%s: %s: %s",
                domain,
                type(e).__name__,
                e,
            )
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
            logger.warning(
                "Twenty upsert_company failed for domain=%s: %s: %s",
                domain,
                type(e).__name__,
                e,
            )
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
            logger.warning(
                "Twenty create_person failed for email=%s: %s: %s",
                email,
                type(e).__name__,
                e,
            )
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
                logger.warning("Twenty create_note returned empty data for person_id=%s", person_id)
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
                logger.warning(
                    "Twenty noteTarget link failed (note %s still created): %s: %s",
                    note["id"],
                    type(e).__name__,
                    e,
                )
            return note
        except Exception as e:
            logger.warning(
                "Twenty create_note failed for person_id=%s: %s: %s",
                person_id,
                type(e).__name__,
                e,
            )
            return None


class NoopTwentyClient:
    """No-op client used when Twenty integration is disabled."""

    async def health_check(self) -> bool:
        return True

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
