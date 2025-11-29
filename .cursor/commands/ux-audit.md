---
description: "Audit the UI implementation against Apple Design Guidelines and SastaSpace standards. Useful for manual UX reviews or when Code-Agent implements frontend features."
globs: []
---

# UX Audit

Review the provided View files (`.erb`) and Stylesheets against the SastaSpace Design System.

## Checklist

### 1. Typography (San Francisco)
*   Are we using the correct font weights? (Regular for body, Semibold for headers)
*   Is hierarchy clear? (Title > Headline > Body > Caption)

### 2. Layout & Spacing (4pt Grid)
*   Check Tailwind classes for padding/margin.
*   Rules:
    *   `p-4` (16px) standard padding.
    *   `gap-4` (16px) or `gap-2` (8px).
    *   Avoid arbitrary values (e.g., `p-[13px]`).

### 3. Color System
*   **Primary**: `#007AFF` (System Blue).
*   **Backgrounds**: Proper use of `bg-white` vs `bg-gray-50`.
*   **Dark Mode**: Do classes support `dark:` variants?

### 4. Interactions
*   **Active States**: Do buttons have `active:scale-95` or similar feedback?
*   **Transitions**: Are `transition-all duration-300 ease-out` used for "springy" feel?
*   **Empty States**: Is there a helpful empty state with a call to action?

## Output
Provide a critique of the current file:
*   **Good**: What follows the rules well.
*   **To Improve**: Specific lines/classes to change to better match the "Apple" feel.

