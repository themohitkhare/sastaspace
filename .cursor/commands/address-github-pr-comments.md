---
description: "Address pending GitHub PR comments by applying fixes to the codebase."
globs: []
---

# Address GitHub PR Comments

You are tasked with resolving code review comments from a GitHub Pull Request.

## Prerequisites

1.  **Identify the PR**: If not provided, ask the user for the PR number or URL.
2.  **Fetch Comments**:
    *   If available, use `mcp_github_pull_request_read` (method: `get_review_comments`) to fetch pending comments.
    *   Alternatively, ask the user to paste the comments or provide the context.
3.  **Analyze Context**: Read the relevant files mentioned in the comments using `read_file`.

## Execution Steps

For each comment:

1.  **Locate Code**: Find the specific line(s) referred to in the file.
2.  **Understand Feedback**: interpret the reviewer's request (e.g., style fix, logic error, missing test, refactor).
3.  **Apply Fix**:
    *   Use `search_replace` or `write` to apply the changes.
    *   Ensure the fix follows the project's Rails 8 and "Apple-like" quality standards.
4.  **Verify**:
    *   If the change is substantial, run relevant tests using `rails test <file>`.
    *   Check for linter errors if applicable.

## Completion

*   After applying fixes, summarize the changes made.
*   (Optional) If using MCP, you can draft a reply to the comment using `mcp_github_add_comment_to_pending_review` (if appropriate) or simply instruct the user to push the changes.

