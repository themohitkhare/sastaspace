---
description: "Generate a Pull Request title and description based on the current git diff. Use this when acting as Code-Agent to create PRs."
globs: []
---

# Create Pull Request Description

Generate a structured PR description based on the uncommitted changes or the difference between the current branch and `main`.

> **Note**: This is used by Code-Agent when creating PRs. Ensure the PR is labeled `ready: review` to trigger Review-Agent workflow.

## Steps

1.  **Analyze Changes**:
    *   Run `git diff main...HEAD --stat` to see touched files.
    *   Run `git diff main...HEAD` (or read specific modified files) to understand the logic.

2.  **Identify Context**:
    *   Look for related issue numbers (e.g., "Closes #123") or Todo items.
    *   Determine the "Why" (User benefit) and the "How" (Technical implementation).

3.  **Generate Content**:
    Create a PR description using the following template:

    ```markdown
    ## Title
    [feat|fix|chore|refactor]: <Concise description>

    ## Summary
    A brief explanation of what this PR does and why.

    ## Changes
    - **Backend**: [List key backend changes]
    - **Frontend**: [List key frontend changes]
    - **Tests**: [Mention added/modified tests]

    ## Implementation Details
    - [Explain any complex logic or architectural decisions]
    - [Mention any new dependencies or migrations]

    ## Screenshots/Video (if UI changes)
    [Placeholder]

    ## Checklist
    - [ ] Tests pass (`rails test`)
    - [ ] Linter passes (`rubocop`)
    - [ ] No sensitive data exposed
    ```

4.  **Output**:
    *   Present the generated markdown to the user.
    *   (Optional) If requested, use `mcp_github_create_pull_request` to open it directly.

