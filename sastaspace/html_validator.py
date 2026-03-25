# sastaspace/html_validator.py
"""Post-generation HTML validation: accessibility, responsiveness, structure."""

import asyncio
import base64
import contextlib
import logging

logger = logging.getLogger(__name__)


def _get_browserless_url() -> str | None:
    """Read browserless_url from settings if available."""
    try:
        from sastaspace.config import Settings

        settings = Settings()
        url = getattr(settings, "browserless_url", None)
        return url if isinstance(url, str) else None
    except Exception:
        return None


def _html_to_data_uri(html: str) -> str:
    """Encode HTML as a data URI so it works with both local and remote browsers."""
    encoded = base64.b64encode(html.encode()).decode()
    return f"data:text/html;base64,{encoded}"


@contextlib.asynccontextmanager
async def _browser(browserless_url: str | None = None):
    """Connect to remote Browserless via CDP, or fall back to local Chromium."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        if browserless_url:
            browser = await pw.chromium.connect_over_cdp(browserless_url)
        else:
            browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def validate_accessibility(html: str) -> dict:
    """Run axe-core accessibility audit on generated HTML.

    Returns dict with 'violations' list and 'passes' count.
    Failures are logged but never raised — this is a non-blocking quality check.
    """
    try:
        browserless_url = _get_browserless_url()
        data_uri = _html_to_data_uri(html)

        async with _browser(browserless_url) as browser:
            page = await browser.new_page()
            await page.goto(data_uri, wait_until="load")

            # Inject axe-core from CDN and run the audit
            await page.add_script_tag(
                url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js"
            )
            results = await page.evaluate("() => axe.run()")
            await page.close()

        violations = results.get("violations", [])
        passes = len(results.get("passes", []))

        # Classify critical/serious violations
        critical = [v for v in violations if v.get("impact") in ("critical", "serious")]
        if critical:
            logger.warning(
                "A11Y | %d critical/serious violations found",
                len(critical),
            )
            for v in critical[:5]:
                logger.warning(
                    "A11Y | %s: %s (%d nodes)",
                    v["impact"],
                    v["description"],
                    len(v.get("nodes", [])),
                )
        else:
            logger.info("A11Y | PASS | %d checks passed, 0 critical violations", passes)

        return {
            "violations": violations,
            "critical_count": len(critical),
            "pass_count": passes,
            "total_violations": len(violations),
        }
    except Exception as e:
        logger.warning("A11Y validation skipped: %s", e)
        return {"violations": [], "critical_count": 0, "pass_count": 0, "error": str(e)}


async def validate_responsiveness(html: str) -> dict:
    """Screenshot at 3 viewport widths and check for horizontal overflow.

    Returns a dict keyed by viewport name with overflow detection results.
    Failures are logged but never raised — this is a non-blocking quality check.
    """
    viewports = [(375, 812, "mobile"), (768, 1024, "tablet"), (1440, 900, "desktop")]
    results = {}

    try:
        browserless_url = _get_browserless_url()
        data_uri = _html_to_data_uri(html)

        async with _browser(browserless_url) as browser:
            for width, height, name in viewports:
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(data_uri, wait_until="load")
                await page.wait_for_timeout(1000)

                # Check for horizontal overflow
                overflow_js = (
                    "() => document.documentElement.scrollWidth"
                    " > document.documentElement.clientWidth"
                )
                has_overflow = await page.evaluate(overflow_js)
                results[name] = {"width": width, "has_overflow": has_overflow}

                if has_overflow:
                    logger.warning(
                        "RESPONSIVE | %s (%dpx): horizontal overflow detected", name, width
                    )

                await page.close()
    except Exception as e:
        logger.warning("Responsiveness validation skipped: %s", e)
        return {"error": str(e)}

    return results


async def run_post_generation_validation(html: str) -> dict:
    """Run all post-generation validations concurrently.

    Returns a combined results dict. Non-blocking — exceptions are caught
    inside each validator so this never raises.
    """
    a11y_result, responsive_result = await asyncio.gather(
        validate_accessibility(html),
        validate_responsiveness(html),
    )
    return {
        "accessibility": a11y_result,
        "responsiveness": responsive_result,
    }
