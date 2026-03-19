# SastaHero Animations & Brutalist Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 20 game-feel animations and align SastaHero's visual design with the SastaSpace brutalist system.

**Architecture:** CSS-first animations (keyframes in index.css, utilities in tailwind.config.js). All animations use only `transform` and `opacity` (GPU-composited). React state drives animation triggers via CSS class toggling. No animation libraries.

**Tech Stack:** React 18, Tailwind CSS 3.3.6, CSS Keyframes, Zustand, Vite

**Worktree:** `/Users/mkhare/Development/sastaspace-hero-juice` (branch: `feat/sastahero-animations-brutalist`)

**Spec:** `docs/sastahero/specs/2026-03-19-animations-brutalist-design.md`

**Z-index stacking order:** Modal overlays (50) > Stage complete banner (40) > Shard burst particles (30) > Milestone popup (25) > Swipe direction label (20) > Scanline overlay (10) > Card stack (1). BottomNav: z-50.

---

## File Map

| File | Changes |
|------|---------|
| `src/index.css` | Add 15+ new keyframes, scanline overlay, update reduced-motion |
| `tailwind.config.js` | Add animation utilities, extend theme |
| `src/components/BottomNav.jsx` | Brutalist restyle + sliding indicator (Anim 19) |
| `src/components/ShardBar.jsx` | HUD readout + counter bump (Anim 6) |
| `src/components/CardDisplay.jsx` | Scanline overlay + card back + border-brutal |
| `src/components/CardFeed.jsx` | Card stack depth (Anim 4) + flip entrance (Anim 1) + reroll spin (Anim 10) |
| `src/components/SwipeHandler.jsx` | Swipe trail (Anim 2) + label pop (Anim 3) + idle breathe (Anim 20) |
| `src/components/QuizCard.jsx` | Brutalist restyle + timer pulse (Anim 11) + correct/wrong (Anim 12, 13) |
| `src/components/PowerupPanel.jsx` | Brutalist restyle + panel slide (Anim 9) + activation burst (Anim 8) |
| `src/components/MilestonePopup.jsx` | Unlock animation (Anim 15) |
| `src/components/BreakSuggestion.jsx` | Brutalist restyle |
| `src/pages/GameFeed.jsx` | Stage complete banner (Anim 14) + shard burst (Anim 5) + combo (Anim 7) |
| `src/pages/CollectionBook.jsx` | Dense grid + brutalist borders + discovery reveal (Anim 17) |
| `src/pages/StoryThread.jsx` | Terminal narrative style |
| `src/pages/KnowledgeBank.jsx` | Fact blocks + pill filters |
| `src/pages/ProfilePage.jsx` | Stats HUD + streak fire (Anim 16) |
| `src/App.jsx` | Page slide transitions (Anim 18) |

All paths relative to `frontends/sastahero/`.

---

## Tasks

16 tasks covering all 20 animations and 10 brutalist alignment items. Each task is self-contained with test + commit steps. Tasks should be executed in order (later tasks depend on CSS from Task 1).

### Task 1: Foundation — CSS Keyframes & Tailwind Config
### Task 2: Brutalist BottomNav + Sliding Indicator (Animation 19)
### Task 3: Brutalist ShardBar + Counter Bump (Animation 6)
### Task 4: CardDisplay — Scanline Overlay + Border Brutal
### Task 5: Card Stack Depth + Flip Entrance + Reroll Spin (Animations 1, 4, 10)
### Task 6: Swipe Trail + Label Pop + Idle Breathe (Animations 2, 3, 20)
### Task 7: Shard Burst + Combo Multiplier + Stage Banner (Animations 5, 7, 14)
### Task 8: Brutalist QuizCard + Timer/Feedback Animations (Animations 11, 12, 13)
### Task 9: Brutalist PowerupPanel + Animations (Animations 8, 9)
### Task 10: Milestone Unlock Animation (Animation 15)
### Task 11: Brutalist BreakSuggestion
### Task 12: Brutalist CollectionBook + Discovery Reveal (Animation 17)
### Task 13: Terminal StoryThread + Brutalist KnowledgeBank
### Task 14: Brutalist ProfilePage + Streak Fire (Animation 16)
### Task 15: Page Slide Transitions (Animation 18)
### Task 16: Final Verification — Full Test Suite + Quality Gates

See the full detailed plan with complete code for each task in the conversation context where this plan was created. Each task includes exact file rewrites, test commands, and commit messages.
