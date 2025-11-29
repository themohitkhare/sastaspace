---
description: "Run a code review checklist against the current changes focusing on Rails best practices, security, and style. Note: Review-Agent handles this automatically in CI, but this is useful for manual reviews."
globs: []
---

# Code Review Checklist

Run this checklist against the current changeset (`git diff` or active files) to ensure compliance with SastaSpace standards.

> **Note**: The Review-Agent workflow (`.github/workflows/agent_orchestration.yml`) automatically runs Rubocop, Brakeman, and tests on PRs. This command is for manual reviews or pre-commit checks.

## 1. Rails & Architecture Standards
- [ ] **Rails 8 Idioms**: Are we using modern Rails features (e.g., `solid_queue`, `solid_cache` if applicable, `generates_token_for`)?
- [ ] **Hotwire**: Are we using Turbo Frames/Streams instead of custom JS where possible?
- [ ] **Stimulus**: Are controllers focused and reusable?
- [ ] **Service Objects**: Is complex business logic moved out of Controllers/Models into `app/services/`?
- [ ] **N+1 Queries**: Check for missing `.includes` or `.preload` in loops.

## 2. Security (Critical)
- [ ] **Strong Parameters**: Are all controller params whitelisted?
- [ ] **Authorization**: Is `current_user` used to scope data? (e.g., `current_user.posts` vs `Post.find`)
- [ ] **Injection**: specific checks for raw SQL or unsafe `html_safe` usage.
- [ ] **PII**: Ensure no sensitive data is logged.

## 3. Testing
- [ ] **Coverage**: Do new features have corresponding unit tests?
- [ ] **Hard-coding**: Are we using `SecureRandom` or Factories instead of hardcoded IDs/strings in tests?
- [ ] **Isolation**: Do tests run independently?

## 4. Apple-Like UI/UX (Frontend)
- [ ] **Typography**: Is the font hierarchy clear? (San Francisco inspired)
- [ ] **Spacing**: Are we adhering to the 4pt grid system?
- [ ] **Feedback**: Do interactions have hover states, active states, or Turbo feedback?
- [ ] **Accessibility**: Are ARIA labels present? WCAG AA compliant?

## 5. Clean Code
- [ ] **Naming**: variable names are descriptive (`user_signed_in?` vs `check_user`).
- [ ] **Rubocop**: Does the code pass the linter?

## Instructions for Agent
1.  Read the changed files.
2.  Go through each point above.
3.  If a violation is found, report it and suggest a fix.
4.  If the code passes a check, mentally check it off (no need to output "passed" for everything, just focus on issues).

