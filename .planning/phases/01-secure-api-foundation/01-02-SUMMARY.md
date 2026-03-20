---
phase: 01-secure-api-foundation
plan: 02
subsystem: api
tags: [fastapi, sse, rate-limiting, nh3, sanitization, concurrency]

# Dependency graph
requires:
  - phase: 01-secure-api-foundation/01
    provides: FastAPI app factory, Settings with CORS/rate-limit fields, conftest fixtures, CORS middleware
provides:
  - POST /redesign SSE endpoint with full pipeline (crawl -> redesign -> deploy)
  - Rate limiting (sliding window, 3/hour/IP, localhost exempt)
  - Concurrency cap (asyncio.Semaphore(1))
  - nh3 HTML sanitization before deployment
  - SSE streaming with named events (crawling/redesigning/deploying/done/error)
  - Full test coverage for all Phase 1 behaviors (24 server tests)
affects: [02-nextjs-scaffold, 03-core-ui]

# Tech tracking
tech-stack:
  added: [format_sse_event from fastapi.sse, nh3.clean]
  patterns: [EventSourceResponse with format_sse_event for SSE streaming, closure-scoped rate limiter and semaphore inside make_app]

key-files:
  created: []
  modified:
    - sastaspace/server.py
    - tests/test_server.py
    - tests/conftest.py

key-decisions:
  - "Used format_sse_event + EventSourceResponse instead of ServerSentEvent objects (Approach A requires manual formatting)"
  - "Rate limiter and semaphore are closure variables inside make_app for test isolation"
  - "TestClient reports host as 'testclient' so localhost exemption tests use X-Forwarded-For header"

patterns-established:
  - "SSE streaming via async generator yielding format_sse_event bytes wrapped in EventSourceResponse"
  - "Pipeline mocking via patch('sastaspace.server.crawl/redesign/deploy') for isolated endpoint testing"
  - "Concurrency testing via threading.Event to block first request while sending second"

requirements-completed: [API-01, API-02, API-03, API-04, API-05, API-06]

# Metrics
duration: 9min
completed: 2026-03-20
---

# Phase 01 Plan 02: SSE /redesign Endpoint Summary

**POST /redesign SSE endpoint with rate limiting, nh3 sanitization, concurrency cap, and 10 endpoint tests covering all Phase 1 behaviors**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-20T22:48:44Z
- **Completed:** 2026-03-20T22:58:20Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fully implemented POST /redesign SSE endpoint streaming crawl -> redesign -> deploy pipeline with named events and progress values
- Added sliding window IP rate limiting (3/hour, localhost exempt) and asyncio.Semaphore(1) concurrency cap
- Implemented nh3 HTML sanitization stripping script tags from LLM output before deployment
- Completed all 10 Phase 1 endpoint tests with full assertions (zero skipped, 66 total tests passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement /redesign SSE endpoint** - `0146cdb` (feat)
2. **Task 2: Complete all Phase 1 tests** - `e5146a9` (test)

## Files Created/Modified
- `sastaspace/server.py` - Added /redesign endpoint, rate limiter, concurrency cap, SSE generator, IP extraction
- `tests/test_server.py` - Replaced 7 stub tests with implementations, added 3 more (done payload, crawl error, redesign error)
- `tests/conftest.py` - Added redesign_client fixture with mocked pipeline

## Decisions Made
- Used `format_sse_event()` + `EventSourceResponse` instead of yielding `ServerSentEvent` objects directly. FastAPI's Approach A (manually returning EventSourceResponse with a generator) requires the generator to yield bytes/strings, not ServerSentEvent model instances. The `format_sse_event` function produces correctly formatted SSE bytes.
- Rate limiter and semaphore are closure variables inside `make_app()` rather than module globals, ensuring each `make_app()` call in tests gets fresh state.
- TestClient reports `request.client.host` as `"testclient"` (not `127.0.0.1`), so the localhost exemption test uses `X-Forwarded-For: 127.0.0.1` header to simulate localhost.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ServerSentEvent objects cannot be yielded in EventSourceResponse generator**
- **Found during:** Task 2 (test_redesign_sse_stream)
- **Issue:** EventSourceResponse wraps a StreamingResponse which expects its generator to yield strings/bytes. Yielding ServerSentEvent Pydantic model objects caused `AttributeError: 'ServerSentEvent' object has no attribute 'encode'`. The plan specified `ServerSentEvent` objects but this only works when using `response_class=EventSourceResponse` on the decorator (Approach B), not Approach A.
- **Fix:** Changed generator to use `format_sse_event(data_str=..., event=...)` which returns properly formatted SSE bytes.
- **Files modified:** sastaspace/server.py
- **Verification:** All SSE tests pass, events correctly formatted
- **Committed in:** e5146a9 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix was necessary for SSE to function. No scope creep.

## Issues Encountered
None beyond the SSE formatting deviation documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired with no placeholder data.

## Next Phase Readiness
- Phase 1 API foundation is complete: CORS, rate limiting, concurrency cap, SSE streaming, nh3 sanitization
- All 66 tests pass (zero failures, zero skipped)
- Ready for Phase 2 (Next.js scaffold) which will consume the POST /redesign endpoint

---
## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 01-secure-api-foundation*
*Completed: 2026-03-20*
