# sastaspace/vikunja_sync.py
"""Vikunja integration — track leads from SastaSpace redesigns as tasks."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class VikunjaClient:
    """Async client for Vikunja REST API v1."""

    def __init__(self, base_url: str, api_token: str, project_id: int):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=_DEFAULT_TIMEOUT,
        )

    async def health_check(self) -> bool:
        """Verify Vikunja is reachable."""
        try:
            resp = await self.client.get("/info")
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Vikunja health check failed: %s", e)
            return False

    async def create_task(
        self,
        title: str,
        description: str = "",
    ) -> int | None:
        """Create a new task in the leads project. Returns task ID or None."""
        try:
            resp = await self.client.put(
                f"/projects/{self.project_id}/tasks",
                json={
                    "title": title,
                    "description": description,
                },
            )
            resp.raise_for_status()
            task_id = resp.json().get("id")
            logger.info("Vikunja task created: %s (%s)", task_id, title)
            return task_id
        except Exception as e:
            logger.warning("Failed to create Vikunja task: %s %s", type(e).__name__, e)
            return None

    async def find_task_by_title(self, title: str) -> dict | None:
        """Find existing task by title search."""
        try:
            resp = await self.client.get("/tasks", params={"s": title})
            resp.raise_for_status()
            tasks = resp.json()
            for task in tasks:
                if task.get("title") == title:
                    return task
            return None
        except Exception as e:
            logger.warning("Failed to search Vikunja tasks: %s", e)
            return None

    async def update_task(self, task_id: int, data: dict) -> bool:
        """Update an existing task."""
        try:
            resp = await self.client.post(f"/tasks/{task_id}", json=data)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.warning("Failed to update Vikunja task %s: %s", task_id, e)
            return False

    async def create_or_update_lead(
        self,
        domain: str,
        job_id: str,
        tier: str = "free",
        subdomain: str = "",
        site_title: str = "",
    ) -> int | None:
        """Create or update a lead task for a redesign job."""
        title = f"{site_title or domain}"
        description = f"**Domain:** {domain}\n**Job ID:** {job_id}\n**Tier:** {tier}\n"
        if subdomain:
            description += f"**Preview:** https://{subdomain}.sastaspace.com\n"

        existing = await self.find_task_by_title(title)
        if existing:
            await self.update_task(
                existing["id"],
                {"description": description},
            )
            return existing["id"]
        return await self.create_task(title, description)


class NoopVikunjaClient:
    """No-op client when Vikunja is not configured."""

    async def health_check(self) -> bool:
        return True

    async def create_task(self, **kwargs) -> None:
        return None

    async def find_task_by_title(self, title: str) -> None:
        return None

    async def update_task(self, task_id: int, data: dict) -> bool:
        return True

    async def create_or_update_lead(self, **kwargs) -> None:
        return None


def get_vikunja_client(
    vikunja_url: str, vikunja_token: str, vikunja_project_id: int
) -> VikunjaClient | NoopVikunjaClient:
    """Factory — returns NoopVikunjaClient when vikunja_url is empty."""
    if not vikunja_url:
        return NoopVikunjaClient()
    return VikunjaClient(
        base_url=vikunja_url, api_token=vikunja_token, project_id=vikunja_project_id
    )
