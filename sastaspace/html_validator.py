# sastaspace/html_validator.py
"""Post-generation HTML validation: accessibility, responsiveness, structure."""

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def validate_accessibility(html: str) -> dict:
    """Run axe-core accessibility audit on generated HTML.

    Returns dict with 'violations' list and 'passes' count.
    Failures are logged but never raised — this is a non-blocking quality check.
    """
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html)
        tmp_path = f.name

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"file://{tmp_path}")

            # Inject axe-core from CDN and run the audit
            await page.add_script_tag(
                url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js"
            )
            results = await page.evaluate("() => axe.run()")

            await browser.close()

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
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def validate_responsiveness(html: str) -> dict:
    """Screenshot at 3 viewport widths and check for horizontal overflow.

    Returns a dict keyed by viewport name with overflow detection results.
    Failures are logged but never raised — this is a non-blocking quality check.
    """
    viewports = [(375, 812, "mobile"), (768, 1024, "tablet"), (1440, 900, "desktop")]
    results = {}

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html)
        tmp_path = f.name

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            for width, height, name in viewports:
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(f"file://{tmp_path}")
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

            await browser.close()
    except Exception as e:
        logger.warning("Responsiveness validation skipped: %s", e)
        return {"error": str(e)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)

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
