---
status: partial
phase: 03-core-ui-landing-progress-result
source: [03-VERIFICATION.md]
started: 2026-03-21T00:00:00Z
updated: 2026-03-21T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Landing page visual quality and Spotlight animation
expected: Animated spotlight subtly moves across the background; hero section looks professional and high-design per LAND-04
result: pending

### 2. URL input form — submit with invalid URL shows error
expected: Typing 'notaurl' or leaving blank and clicking 'Redesign My Site' shows 'Please enter a valid website address' inline error
result: pending

### 3. URL input form — favicon preview appears
expected: After typing a domain like 'example.com', the Globe icon is replaced by the site's favicon.ico within ~500ms
result: pending

### 4. Landing to progress transition
expected: Submitting a valid URL (with backend running at localhost:8080) animates the landing view out and the progress view in without a full page reload
result: pending

### 5. Progress view — per-step bars advance with personalized labels
expected: Each SSE event shows a domain-personalized label (e.g. 'Analyzing example.com') and the matching progress bar advances determinately; previous steps show check icons
result: pending

### 6. Progress view — NO time estimate shown
expected: No '~45 seconds' or any countdown appears anywhere on the progress screen (PROG-05 intentionally omitted per D-07)
result: pending

### 7. Error state with retry
expected: Killing the backend mid-stream shows 'Something went wrong' with a 'Try again' button; clicking it restarts the request
result: pending

### 8. Result page — blurred iframe with CTA
expected: Navigating to /acme-corp/ shows a blurred iframe preview with 'Take me to the future' button overlaid; clicking the button navigates same-tab to /acme-corp/
result: pending

### 9. Result page — 'View original site' opens new tab
expected: Clicking 'View original site' opens https://acme.corp in a new browser tab
result: pending

### 10. Result page — shareable URL copy adapts
expected: Visiting /acme-corp/ directly shows 'acme.corp has been redesigned'; navigating from progress flow shows 'Your new acme.corp is ready'
result: pending

### 11. Mobile responsiveness at 375px
expected: URL input stacks vertically; how-it-works steps stack vertically with vertical connectors; result iframe uses 4:3 aspect ratio
result: pending

## Summary

total: 11
passed: 0
issues: 0
pending: 11
skipped: 0
blocked: 0

## Gaps
