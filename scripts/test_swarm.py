#!/usr/bin/env python3
"""Quick test script for the swarm redesign pipeline.

Usage:
    uv run python scripts/test_swarm.py https://example.com

Requires claude-code-api running on localhost:8000.
"""
import asyncio
import json
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sastaspace.com"

    from sastaspace.config import Settings
    from sastaspace.crawler import crawl

    settings = Settings()

    print(f"\n{'='*60}")
    print(f"SWARM PIPELINE TEST — {url}")
    print(f"{'='*60}\n")

    # Step 1: Crawl
    print("[1/2] Crawling...")
    t0 = time.time()
    crawl_result = await crawl(url)
    if crawl_result.error:
        print(f"Crawl failed: {crawl_result.error}")
        sys.exit(1)
    print(f"  Crawled in {time.time()-t0:.1f}s — {len(crawl_result.text_content)} chars, {len(crawl_result.images)} images")

    # Step 2: Swarm pipeline
    print("[2/2] Running swarm pipeline...")

    def on_progress(phase, data):
        print(f"  -> {phase}: {json.dumps(data)[:100]}")

    from sastaspace.swarm import SwarmOrchestrator

    orchestrator = SwarmOrchestrator(
        api_url=settings.claude_code_api_url,
        api_key=settings.claude_code_api_key,
        progress_callback=on_progress,
    )

    t1 = time.time()
    result = await asyncio.to_thread(orchestrator.run, crawl_result)
    elapsed = time.time() - t1

    print(f"\n{'='*60}")
    print(f"RESULT")
    print(f"{'='*60}")
    print(f"  HTML length: {len(result.html)} chars")
    print(f"  Iterations:  {result.iterations}")
    print(f"  Phases:      {', '.join(result.phases_completed)}")
    print(f"  QA passed:   {result.quality_report.get('passed', 'N/A')}")
    print(f"  Duration:    {elapsed:.1f}s")

    if result.quality_report.get("static", {}).get("failures"):
        print(f"\n  Static failures:")
        for f in result.quality_report["static"]["failures"]:
            print(f"    - {f}")

    # Save output
    out_path = f"sites/_swarm_test/index.html"
    import os
    os.makedirs("sites/_swarm_test", exist_ok=True)
    with open(out_path, "w") as f:
        f.write(result.html)
    print(f"\n  Saved to: {out_path}")
    print(f"  View: open {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
