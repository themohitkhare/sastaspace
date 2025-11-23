---
description: "Draft release notes by analyzing the git log and categorizing changes."
globs: []
---

# Draft Release Notes

Generate user-facing release notes from the recent commit history.

## 1. Fetch History
Run `git log --oneline <since_tag>..HEAD` (ask user for the `since_tag`, e.g., `v1.2.0`).

## 2. Categorize
Group the commits into:
*   **✨ New Features**: Stuff users can actually do now.
*   **🐛 Bug Fixes**: Stuff that works correctly now.
*   **⚡ Performance**: Speed improvements.
*   **🛡️ Privacy/Security**: Security updates (important for SastaSpace users).

## 3. Draft Notes
Write the release notes in a friendly, "Apple-style" tone (concise, benefit-focused).

*Example*:
> **SastaSpace 1.3**
>
> **Shoe Analysis**
> Your closet just got smarter. SastaSpace can now recognize and categorize your footwear automatically using our local AI.
>
> **Improvements**
> *   Fixed an issue where the scanner would freeze on large images.
> *   Optimized database storage for faster loading.

## 4. Technical Changelog (Optional)
Append a raw list of commits for internal reference.

