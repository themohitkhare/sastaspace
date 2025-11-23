---
description: "List and analyze GitHub issues to prioritize work."
globs: []
---

# Triage Issues

Review open GitHub issues to help the Product Manager prioritize.

## Steps

1.  **Fetch Issues**:
    Use `mcp_github_list_issues` to get the latest open issues (limit: 20).

2.  **Analyze**:
    For each issue, determine:
    *   **Clarity**: Is the problem well-defined?
    *   **Priority**:
        *   P0: Critical Bug / Blocker
        *   P1: High Value Feature
        *   P2: Nice to have
    *   **Category**: Backend, Frontend, AI, DevOps.

3.  **Report**:
    Generate a table summarizing the triage:

    | Issue | Title | Priority | Category | Action Needed |
    | :--- | :--- | :--- | :--- | :--- |
    | #123 | Fix login crash | P0 | Backend | Assign to dev |
    | #124 | Add dark mode | P1 | Frontend | Needs designs |

4.  **Action (Optional)**:
    *   If an issue is unclear, offer to draft a clarifying comment using `mcp_github_add_issue_comment`.
    *   If an issue needs a label, use `mcp_github_issue_write` to add labels like `bug`, `enhancement`.

