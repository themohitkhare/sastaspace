# Sub-app Shell + Advanced Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every sub-app feel “unstuck” (one-click back to the SastaSpace hub) and keep default flows “one click → value” by hiding power options behind **Advanced**.

**Architecture:** Add a lightweight, consistent header/shell to each sub-app (Sudoku + SastaDice + static pages), then introduce “Advanced” toggles for Sudoku and SastaDice. Keep changes local to each frontend to avoid cross-build coupling.

**Tech Stack:** React (Vite), react-router, static nginx-served pages, Traefik path prefixes.

---

### Task 1: Add a shared “Back to SastaSpace” header to Sudoku

**Files:**
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/App.jsx`
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/index.css`
- Test: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/App.test.jsx` (if needed)

**Step 1: Write/adjust test (optional)**
- Ensure header renders “SASTASPACE” and links to `/`.

**Step 2: Implement minimal header**
- In `App.jsx`, change header markup to include a left anchor `<a href="/" ...>SASTASPACE</a>` and app name.
- Keep Sudoku’s router basename as-is.

**Step 3: Style header**
- Reuse brutalist styling already applied in Sudoku CSS.

**Step 4: Verify**
- Run: `cd frontends/sudoku && npm test`
- Run: `cd frontends/sudoku && npm run build`

---

### Task 2: Add the same “Back to SastaSpace” header to SastaDice

**Files:**
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sastadice/src/App.jsx` (or a top-level layout component if present)
- Test: `/Users/mkhare/Development/sastaspace/frontends/sastadice/tests/*` (if affected)

**Step 1: Implement header**
- Add a sticky top header (brutalist style already exists across SastaDice) with:
  - `<a href="/" ...>SASTASPACE</a>`
  - App label “SASTADICE”

**Step 2: Verify**
- Run SastaDice frontend tests if available (bun/vitest depending on scripts).
- Smoke via curl: `curl -s http://localhost/sastadice/` returns HTML.

---

### Task 3: Add “Advanced” toggle for Sudoku (or remove unused controls)

**Files:**
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/pages/Sudoku.jsx`
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/index.css`
- Test: `/Users/mkhare/Development/sastaspace/frontends/sudoku/src/pages/Sudoku.test.jsx` (create if needed) or extend existing tests

**Step 1: Decide which controls are real**
- If `difficulty` and `gridSize` should remain: expose under Advanced.
- If not: remove state + request fields from `startMatch`.

**Step 2: Implement Advanced UI (if keeping)**
- Add `showAdvanced` state.
- Add small “Advanced” button/summary under the main CTA that reveals:
  - Difficulty picker (easy/medium/hard)
  - Grid size if intended (otherwise omit)

**Step 3: Verify**
- `npm test` + `npm run build`

---

### Task 4: Add “Advanced” toggle for SastaDice CPU selection

**Files:**
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sastadice/src/pages/HomePage.jsx`

**Step 1: Implement progressive disclosure**
- Default view shows primary CTAs:
  - Create game
  - Join game
- Add “Advanced” expander: “Add CPU opponents”
- Move the CPU grid under it (collapsed by default).

**Step 2: Verify**
- Ensure create/join flows still work.

---

### Task 5: Normalize static sub-app “back to hub”

**Files:**
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sastahero/index.html` (if present) or the mounted directory file used by nginx
- Modify: `/Users/mkhare/Development/sastaspace/frontends/sasta/index.html`

**Step 1: Add a consistent “Back to SastaSpace” button**
- Ensure both pages link to `/`.

---

### Task 6: Local navigation regression checks

**Checks:**
- Hub → Sudoku → hub works with one click.
- Hub → SastaDice → hub works with one click.
- `http://localhost/sasta/` and `http://localhost/sastahero/` both load and link back to `/`.
- Deep link refresh works:
  - `http://localhost/sudoku/<matchId>` (after creating a match)
  - `http://localhost/sastadice/lobby/<gameId>` (if you have one)

**Commands (helpful):**
- `curl -s -I http://localhost/sudoku/ | head`
- `curl -s -I http://localhost/sastadice/ | head`

