# SastaDice Sprint 3: Mobile & Polish — Design Spec

**Date:** 2026-03-19
**Status:** Approved

---

## Goal

Improve mobile responsiveness, add keyboard shortcuts for power users, and add game-feel CSS animations. All frontend-only CSS/JSX changes.

## Scope Decisions

- **4A Mobile**: Add responsive Tailwind breakpoints to existing layout. Skip slide-out drawer for PlayerPanel (YAGNI — stacking order change is sufficient).
- **4B Animations**: CSS keyframes only. Skip particle effects (rent cash flying) — too complex for value. Focus on: property purchase, buff activation, bankruptcy flash, turn transition.
- **4E Keyboard Shortcuts**: Add T/M/R/Escape/1-2-3 to existing keyboard handler in CenterActionButton. Add hint text to buttons.

---

## Changes by File

### 1. GamePage.jsx — Keyboard Handler + Layout Tweaks

**New keyboard shortcuts** (add to existing handler in CenterActionButton, or new useEffect in GamePage):
- `Escape` — Close any open modal (rules, property manager, peek events, trade)
- `T` — Open trade with next non-self player (during your turn)
- `M` — Toggle property manager
- `R` — Toggle rules modal

Since CenterActionButton already owns the keydown listener, we add a SECOND listener in GamePage for modal-level shortcuts (Escape/T/M/R). This avoids prop drilling modal state into CenterActionButton.

**Mobile layout**: The `flex flex-col lg:flex-row` on line 301 already stacks on mobile. Tweak:
- Board section: Add `min-h-[50vh]` on mobile so board isn't crushed
- Right panel: Add `max-h-[40vh] lg:max-h-full` so it scrolls on mobile

### 2. CenterActionButton.jsx — Keyboard Hint Labels + Touch Sizing

**Add hint text to buttons:**
- ROLL DICE → `ROLL DICE [SPACE]`
- END TURN → `END TURN [SPACE]`
- Already has: `BUY [Y]`, `PASS [N]`

**Touch sizing**: Buttons already have `min-h-[44px]` in PlayerPanel. CenterActionButton main buttons are large enough. Add `min-h-[48px]` to the main action buttons for consistent touch targets.

**Auction quick-bid shortcuts** (1/2/3): Add to existing keyboard handler:
- During AUCTION phase: `1` = bid +$10, `2` = bid +$50, `3` = bid +$100

### 3. index.css — Game-Feel Animations

Add 4 new keyframe animations:

**`purchase-sweep`** — Property tile border fills from dashed to solid:
```css
@keyframes purchase-sweep {
  0% { border-style: dashed; opacity: 0.5; }
  50% { border-style: solid; opacity: 0.8; transform: scale(1.05); }
  100% { border-style: solid; opacity: 1; transform: scale(1); }
}
```

**`buff-shimmer`** — Buff badge activation glow:
```css
@keyframes buff-shimmer {
  0%, 100% { box-shadow: 0 0 4px currentColor; }
  50% { box-shadow: 0 0 12px currentColor; }
}
```

**`bankruptcy-flash`** — Red flash on player card:
```css
@keyframes bankruptcy-flash {
  0%, 100% { background-color: transparent; }
  25%, 75% { background-color: rgba(255, 0, 0, 0.3); }
}
```

**`turn-fade`** — Smooth turn transition:
```css
@keyframes turn-fade {
  0% { opacity: 0.6; }
  100% { opacity: 1; }
}
```

Plus Tailwind utility classes for each:
```css
.animate-purchase { animation: purchase-sweep 0.5s ease-out; }
.animate-buff-shimmer { animation: buff-shimmer 1.5s ease-in-out infinite; }
.animate-bankruptcy { animation: bankruptcy-flash 0.6s ease-in-out 2; }
.animate-turn-fade { animation: turn-fade 0.3s ease-in; }
```

### 4. PlayerPanel.jsx — Apply Animations

- Player card: Add `animate-turn-fade` class when `isCurrentTurn` changes
- Bankrupt player: Add `animate-bankruptcy` when `player.is_bankrupt` (one-shot)
- Buff badge: Already has conditional rendering — add `animate-buff-shimmer` to the buff span

### 5. TileComponent.jsx — Purchase Animation

- When tile transitions from unowned (dashed border) to owned (solid border), apply `animate-purchase` class briefly. Since we don't track "just purchased" state, skip this — the polling refresh handles the visual change. The animation utility is available for future use.

---

## Testing Strategy

| Change | Test Approach |
|--------|--------------|
| Keyboard shortcuts | Add to GamePage.test.jsx — simulate keydown events, verify modal state changes |
| Animations | No unit tests for CSS animations — visual verification only |
| Responsive layout | No unit tests — Tailwind classes are declarative |

---

## Files Affected

| File | Action | Lines Added (est.) |
|------|--------|--------------------|
| GamePage.jsx | Modify | ~30 (keyboard handler + layout tweaks) |
| CenterActionButton.jsx | Modify | ~15 (hint labels + auction shortcuts) |
| index.css | Modify | ~40 (4 keyframe animations + utilities) |
| PlayerPanel.jsx | Modify | ~5 (animation classes) |
