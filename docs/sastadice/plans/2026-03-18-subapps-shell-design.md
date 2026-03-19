# SastaSpace Sub-app Shell + Advanced Controls (Approach A + B)

## Background

SastaSpace is a hub that routes users into multiple sub-apps (e.g. Sudoku, SastaDice) via path prefixes on localhost (Traefik).

The product goal is consistent with the “users want speed + clarity” principle:
- One click → one result → leave.
- Power options exist, but only after the user gets value.

## Problem

1. **Navigation trap:** Once a user enters a sub-app, there is no consistent “Back to SastaSpace” affordance. Browser Back is unreliable (new tab, refresh, direct deep-link).
2. **Builder controls leaking into code:** Some sub-apps contain “power” configuration state that is not exposed (or is exposed too early), creating mismatch between UX and implementation.

## Goals

- **G1:** Every sub-app has a consistent “shell” affordance to return to the hub quickly.
- **G2:** Default user path remains minimal: one primary CTA.
- **G3:** Power controls are either removed (if unused) or hidden behind an explicit **Advanced** reveal.

## Non-goals

- Redesigning app flows end-to-end.
- Unifying build tooling across apps (no Tailwind migration for Sudoku as part of this change).
- Introducing cross-app state (e.g. user sessions shared across sub-apps).

## Design

### A) Sub-app Shell (shared header)

Add a lightweight header at the top of each sub-app:

- Left: **SASTASPACE** (click → `/`)
- Center/Right: sub-app name + optional badge (e.g. “GA Solver”)
- Optional: secondary link “Home” (also → `/`) for clarity

This shell should be visually consistent with the hub’s brutalist design language (thick border, brutal shadow, high contrast).

**Target apps**
- `frontends/sudoku` (React SPA)
- `frontends/sastadice` (React SPA)
- `frontends/sastahero` (static HTML)
- `frontends/sasta` (static placeholder HTML, until real app exists)

### B) Advanced Controls (progressive disclosure)

Keep the main path “one click → value”:

- **Sudoku:** Primary CTA remains “Solve with GA”.
  - If difficulty/grid-size controls are needed, add a small “Advanced” toggle showing them.
  - If they are not needed, remove the unused state and keep the interface minimal.

- **SastaDice:** Primary CTA remains “Create game”.
  - CPU selection becomes optional: default to 0 CPUs, or show a single “Add CPUs (Advanced)” section.

## Success criteria

- From any sub-app, the user can return to the hub in **one click** without using the address bar.
- The default screen in each app has **one primary CTA**.
- Advanced options do not block the default path.

## Implementation plan (high-level)

1. Create a tiny shared header component (or copy minimal markup per app if shared deps are messy).
2. Add the header to Sudoku and SastaDice layouts.
3. Add “Advanced” toggles:
   - Sudoku: difficulty (and grid size if intended) behind the toggle or removed.
   - SastaDice: CPU selection behind the toggle or collapsed by default.
4. Verify local navigation:
   - Hub → sub-app → hub works reliably.
   - Deep link refresh (`/sudoku/<id>`, `/sastadice/lobby/<id>`) still works via nginx SPA routing.

## Trade-offs

- Adding a shared header improves navigation clarity but slightly reduces “full-screen” immersion.
- Progressive disclosure reduces friction for new users but may add a click for power users.

