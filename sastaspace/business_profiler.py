# sastaspace/business_profiler.py
"""Business profile extraction via LLM.

Stub module — full implementation in a separate task.
"""

from __future__ import annotations

from sastaspace.models import BusinessProfile


def build_business_profile(
    homepage_text: str,
    internal_pages_text: list[str],
    api_url: str,
    model: str,
    api_key: str,
) -> BusinessProfile:
    """Extract structured business intelligence from crawled page text.

    Stub implementation — returns a minimal profile.
    Full implementation will call the LLM for structured extraction.
    """
    return BusinessProfile()
