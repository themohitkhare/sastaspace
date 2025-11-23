---
description: "Generate a Product Requirements Document (PRD) from a GitHub Issue or concept."
globs: []
---

# Generate PRD

Create a structured Product Requirements Document.

## 1. Gather Context
*   **From User**: Ask for the feature idea or GitHub Issue number.
*   **From GitHub**: If an Issue number is provided, use `mcp_github_issue_read` to fetch the title, body, and comments.

## 2. Generate Document
Based on the input, draft a PRD with the following structure:

```markdown
# PRD: [Feature Name]

## 1. Overview
*   **Problem**: What user pain point are we solving?
*   **Goal**: What is the successful outcome?

## 2. User Stories
*   As a [User], I want to [Action], so that [Benefit].

## 3. UX/UI Requirements (Apple-Quality)
*   **Layout**: [e.g., Grid view with spring animations]
*   **Interactions**: [e.g., Long-press to preview]
*   **Copy**: [Tone: Helpful, concise]

## 4. Technical Constraints (SastaSpace)
*   **AI**: Must run on local Ollama.
*   **Privacy**: No data leaves the device/server.
*   **Stack**: Rails 8 + Hotwire.

## 5. Acceptance Criteria
*   [ ] Scenario A
*   [ ] Scenario B
```

## 3. Refine
Ask the user for feedback on the draft and iterate.

