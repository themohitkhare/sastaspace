---
description: "Perform a light-weight review of the current uncommitted changes (git diff). Useful for quick pre-commit checks before Code-Agent creates a PR."
globs: []
---

# Light Review of Existing Diffs

Analyze the current working directory changes (`git diff`) before committing.

## Instructions

1.  **Get Diff**: Run `git diff` to see unstaged changes. (If empty, run `git diff --staged`).
2.  **Review**:
    *   **Sanity Check**: Are there any left-over `binding.pry`, `console.log`, or debug prints?
    *   **Structure**: Does the code look clean and indented?
    *   **Logic**: Are there obvious bugs or off-by-one errors?
    *   **Safety**: Any sensitive keys or PII hardcoded?
3.  **Report**:
    *   List any immediate issues found.
    *   If the code looks good, provide a suggested commit message following the Conventional Commits format: `<type>(<scope>): <subject>`.

