# sastaspace/espocrm_sync.py
"""EspoCRM integration — create leads from SastaSpace redesigns."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Default timeout for all EspoCRM API calls (connect, read, write, pool)
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class EspoCRMClient:
    """Async client for EspoCRM REST API v1."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=_DEFAULT_TIMEOUT,
        )

    async def health_check(self) -> bool:
        """Verify EspoCRM is reachable and API key is valid."""
        try:
            resp = await self.client.get("/App/user")
            return resp.status_code == 200
        except Exception as e:
            logger.warning("EspoCRM health check failed: %s", e)
            return False

    async def create_lead(
        self,
        first_name: str,
        last_name: str,
        email: str,
        website: str,
        description: str = "",
        source: str = "Web Site",
    ) -> str | None:
        """Create a new Lead in EspoCRM. Returns lead ID or None."""
        try:
            resp = await self.client.post(
                "/Lead",
                json={
                    "firstName": first_name,
                    "lastName": last_name,
                    "emailAddress": email,
                    "website": website,
                    "description": description,
                    "source": source,
                    "status": "New",
                },
            )
            resp.raise_for_status()
            lead_id = resp.json().get("id")
            logger.info("EspoCRM lead created: %s (%s)", lead_id, email)
            return lead_id
        except Exception as e:
            logger.warning("Failed to create EspoCRM lead: %s %s", type(e).__name__, e)
            return None

    async def find_lead_by_email(self, email: str) -> dict | None:
        """Find existing lead by email address."""
        try:
            resp = await self.client.get(
                "/Lead",
                params={
                    "where[0][type]": "equals",
                    "where[0][attribute]": "emailAddress",
                    "where[0][value]": email,
                },
            )
            resp.raise_for_status()
            leads = resp.json().get("list", [])
            return leads[0] if leads else None
        except Exception as e:
            logger.warning("Failed to search EspoCRM leads: %s", e)
            return None

    async def update_lead(self, lead_id: str, data: dict) -> bool:
        """Update an existing lead."""
        try:
            resp = await self.client.put(f"/Lead/{lead_id}", json=data)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.warning("Failed to update EspoCRM lead %s: %s", lead_id, e)
            return False

    async def create_or_update_lead(
        self,
        first_name: str,
        last_name: str,
        email: str,
        website: str,
        description: str = "",
    ) -> str | None:
        """Upsert: find by email, update if exists, create if not."""
        existing = await self.find_lead_by_email(email)
        if existing:
            await self.update_lead(
                existing["id"],
                {
                    "website": website,
                    "description": description,
                },
            )
            return existing["id"]
        return await self.create_lead(first_name, last_name, email, website, description)


class NoopEspoCRMClient:
    """No-op client when EspoCRM is not configured."""

    async def health_check(self) -> bool:
        return True

    async def create_lead(self, **kwargs) -> None:
        return None

    async def find_lead_by_email(self, email: str) -> None:
        return None

    async def update_lead(self, lead_id: str, data: dict) -> bool:
        return True

    async def create_or_update_lead(self, **kwargs) -> None:
        return None


def get_espocrm_client(espocrm_url: str, espocrm_api_key: str) -> EspoCRMClient | NoopEspoCRMClient:
    """Factory — returns NoopEspoCRMClient when espocrm_url is empty."""
    if not espocrm_url:
        return NoopEspoCRMClient()
    return EspoCRMClient(base_url=espocrm_url, api_key=espocrm_api_key)
