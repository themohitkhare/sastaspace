# sastaspace/business_profiler.py
from __future__ import annotations

import json
import logging

from openai import OpenAI

from sastaspace.crawler import CrawlResult
from sastaspace.models import BusinessProfile, PageCrawlResult

logger = logging.getLogger(__name__)

PROFILE_SYSTEM_PROMPT = """You are a business analyst. Given the text content of a website,
extract a structured business profile as JSON. Return ONLY valid JSON with these fields:
business_name, industry, services (list), target_audience, tone, differentiators (list),
social_proof (list), pricing_model, cta_primary, brand_personality."""


def _call_llm(text: str, api_url: str, model: str, api_key: str) -> str:
    """Make a single LLM call for business profiling. Returns raw response text."""
    client = OpenAI(base_url=api_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this website content:\n\n{text[:10000]}"},
        ],
        max_tokens=1000,
    )
    return response.choices[0].message.content or ""


def _parse_profile(raw_json: str) -> BusinessProfile:
    """Parse LLM JSON response into BusinessProfile. Returns minimal profile on failure."""
    try:
        data = json.loads(raw_json)
        return BusinessProfile(
            business_name=data.get("business_name", "unknown"),
            industry=data.get("industry", "unknown"),
            services=data.get("services", []),
            target_audience=data.get("target_audience", "unknown"),
            tone=data.get("tone", "unknown"),
            differentiators=data.get("differentiators", []),
            social_proof=data.get("social_proof", []),
            pricing_model=data.get("pricing_model", "none-found"),
            cta_primary=data.get("cta_primary", "unknown"),
            brand_personality=data.get("brand_personality", "unknown"),
        )
    except (json.JSONDecodeError, AttributeError, TypeError):
        return BusinessProfile()


def build_business_profile(
    homepage: CrawlResult,
    internal_pages: list[PageCrawlResult],
    api_url: str,
    model: str,
    api_key: str,
) -> BusinessProfile:
    """Build a BusinessProfile from crawled page content via LLM.

    Returns a minimal profile with 'unknown' fields if the LLM call fails.
    """
    # Combine text from all pages
    texts = [homepage.text_content]
    for page in internal_pages:
        if not page.error and page.text_content:
            texts.append(page.text_content)
    combined = "\n\n---\n\n".join(texts)

    try:
        raw = _call_llm(combined, api_url, model, api_key)
        profile = _parse_profile(raw)
        # Fallback: use homepage title if business_name is unknown
        if profile.business_name == "unknown" and homepage.title:
            profile.business_name = homepage.title
        return profile
    except Exception:
        logger.warning("Business profiling LLM call failed, returning minimal profile")
        return BusinessProfile(
            business_name=homepage.title if homepage.title else "unknown",
        )
