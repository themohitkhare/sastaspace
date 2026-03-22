# sastaspace/business_profiler.py
"""LLM-powered business profile extraction from crawled pages."""

from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from sastaspace.crawler import CrawlResult
from sastaspace.models import BusinessProfile, PageCrawlResult

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """Analyze these web pages from a single business and extract a structured \
business profile.

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{
  "business_name": "string",
  "industry": "string — e.g. dental, saas, restaurant, legal, ecommerce, agency",
  "services": ["list of specific offerings"],
  "target_audience": "who they serve",
  "tone": "one of: professional, casual, luxurious, friendly, technical, playful, corporate",
  "differentiators": ["what makes them unique"],
  "social_proof": ["testimonials, client names, review counts, awards"],
  "pricing_model": "listed | contact-based | freemium | subscription | none-found",
  "cta_primary": "their main call-to-action text",
  "brand_personality": "2-3 sentence summary of the brand voice and personality"
}"""


def _deduplicate_text(texts: list[str]) -> str:
    """Remove duplicate sentences across pages (header/footer boilerplate).

    The crawler's _extract_text() collapses whitespace into single spaces,
    so we split on sentence boundaries ('. ') rather than newlines.
    """
    all_sentences: list[list[str]] = []
    for text in texts:
        # Split on sentence-ending punctuation followed by space
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        all_sentences.append(sentences)
    result_parts: list[str] = []
    seen: set[str] = set()
    for sentences in all_sentences:
        for s in sentences:
            if s in seen:
                continue
            seen.add(s)
            result_parts.append(s)
    return " ".join(result_parts)


def _call_llm(prompt: str, api_url: str, model: str, api_key: str) -> str:
    """Make a single LLM call for extraction."""
    client = OpenAI(base_url=api_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def build_business_profile(
    homepage: CrawlResult,
    internal_pages: list[PageCrawlResult],
    api_url: str,
    model: str,
    api_key: str,
) -> BusinessProfile:
    """Extract a structured business profile from crawled pages via LLM."""
    texts = [homepage.text_content]
    for p in internal_pages:
        if not p.error:
            texts.append(p.text_content)
    deduped = _deduplicate_text(texts)

    prompt_parts = [
        f"## Homepage: {homepage.title}",
        f"Meta: {homepage.meta_description}",
        f"Headings: {', '.join(homepage.headings[:10])}",
        deduped[:8000],
    ]
    for p in internal_pages:
        if p.error:
            continue
        prompt_parts.append(f"\n## {p.page_type.title()}: {p.title}")
        prompt_parts.append(f"Headings: {', '.join(p.headings[:10])}")
        if p.testimonials:
            prompt_parts.append(f"Testimonials: {' | '.join(p.testimonials[:5])}")
    user_prompt = "\n".join(prompt_parts)

    try:
        raw = _call_llm(user_prompt, api_url, model, api_key)
        # Try to extract JSON from possible markdown fencing
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)
        data = json.loads(raw)
        return BusinessProfile(
            business_name=data.get("business_name", homepage.title),
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
    except Exception as e:
        logger.warning("Business profiling failed, using minimal profile: %s", e)
        return BusinessProfile.minimal(homepage.title)
