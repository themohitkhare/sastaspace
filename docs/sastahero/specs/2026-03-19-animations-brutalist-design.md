# SastaHero: Animations & Brutalist Alignment

**Date:** 2026-03-19
**Status:** Approved
**Approach:** "Juice It" — Animation-rich game feel + full brutalist alignment

## Problem

SastaHero's card game mechanics are solid, but:
1. The game lacks the dopamine-hit animations that make SastaDice feel alive
2. The visual design drifts from SastaSpace's brutalist language — soft gradients, generic mobile UI patterns, inconsistent borders/shadows/typography

## Goals

- Add 20 purposeful animations mapped to every player interaction moment
- Align SastaHero's structural design (borders, shadows, typography, layout) with the SastaSpace brutalist system
- Keep `#ff6600` (orange) as SastaHero's unique accent color
- Maintain `prefers-reduced-motion` accessibility support

## Design Decision: Accent Color

Each sub-app keeps its own accent color (SastaSpace/SastaDice = `#00ff00` green, SastaHero = `#ff6600` orange) while sharing the structural brutalist DNA. This gives each game its own identity within the family.

---

## Part 1: Brutalist Alignment Audit

### Current Deviations

- Card mesh gradients feel modern/soft — clash with raw brutalist vibe
- BottomNav uses generic mobile UI (rounded icons, soft styling)
- Modals lack thick borders and hard shadows
- Some text falls back to sans-serif instead of monospace
- Buttons don't follow the black-bg / accent-hover pattern consistently
- QuizCard and secondary pages feel like a different app

### The SastaSpace Brutalist Standard

| Element | Rule |
|---------|------|
| Borders | Thick, solid, black. 3px minimum. No rounded corners. |
| Shadows | Hard offset (4px 4px 0px black). No blur. |
| Typography | ALL monospace. Headers: uppercase, tracking-widest, font-bold. |
| Colors | Black/white base. One neon accent. No pastels, no gray backgrounds. |
| Buttons | `bg-black text-white border-brutal hover:bg-accent hover:text-black` |
| Spacing | Tight. Information-dense. Not airy. |
| Feel | Terminal meets arcade. CRT aesthetic. |

### Specific Fixes (10 Items)

#### 1. Cards — CRT Scanline Overlay
Add a scanline overlay on top of mesh gradients: subtle repeating horizontal lines (1px, 5% opacity). Keeps the color identity but makes it feel retro/CRT. Add `border-brutal` (3px solid black) around every card.

#### 2. BottomNav — Brutalist Restyle
Thick top border (4px black), no rounded anything, monospace uppercase labels, active tab = orange text + thick underline (not a highlight blob).

#### 3. All Modals — Dark Brutal Panels
Black background, `border-brutal-lg` (4px), `shadow-brutal-lg` (6px offset). White monospace text. No padding luxury.

#### 4. ShardBar — HUD Readout
Tighter spacing, monospace numbers, each shard counter gets `border-brutal-sm` box. Feels like a HUD readout, not a progress bar.

#### 5. QuizCard — Arcade Quiz
Black bg, orange accent for timer ring, brutal borders on answer options, monospace question text. Answer buttons follow standard button pattern.

#### 6. CollectionBook — Dense Grid
Grid slots get `border-brutal-sm`, undiscovered cards show "???" in monospace (not a fancy placeholder). Dense grid, minimal gaps.

#### 7. StoryThread — Terminal Narrative
Narrative text in monospace, indented with `>` prefix (terminal-style, matching SastaSpace landing page quotation blocks). Chapter headers uppercase + tracked.

#### 8. KnowledgeBank — Fact Blocks
Facts displayed as monospace blocks with brutal borders. Category filters as black pill buttons.

#### 9. ProfilePage — Stats HUD
Stats in a tight grid of brutal-bordered boxes. Numbers large + bold. Labels small + uppercase. Streak counter gets fire animation (see Animation #16).

#### 10. Page Backgrounds
Pure black (`#000000`). No dark grays, no subtle gradients on the page level.

---

## Part 2: Animation Inventory (20 Animations)

All animations respect `@media (prefers-reduced-motion: reduce)` — disabled when set. All durations are snappy: ≤0.6s for feedback, ≤1.5s for celebrations. No animation blocks user input.

### Card Interactions (Core Loop)

#### Animation 1: Card Flip Entrance
- **Trigger:** New card appears in deck
- **Effect:** 3D rotateY flip from backface. Card back shows "?" glyph, then reveals front.
- **Duration:** 0.4s ease-out
- **Purpose:** Builds anticipation for each card

#### Animation 2: Swipe Trail
- **Trigger:** Player drags card
- **Effect:** Directional ghost trail (opacity 0.15) follows card during drag
- **Duration:** Continuous during drag, fades 0.2s on release
- **Purpose:** Reinforces direction commitment

#### Animation 3: Swipe Label Pop
- **Trigger:** Swipe crosses 50px threshold
- **Effect:** Direction label ("PLAY", "SYNTHESIZE", etc.) does scale bounce 1.0 → 1.2 → 1.0
- **Duration:** 0.2s ease-out-back
- **Purpose:** Haptic-style confirmation of direction lock

#### Animation 4: Card Stack Depth
- **Trigger:** Always visible behind current card
- **Effect:** 2-3 stacked cards behind current (offset 2px each, scaled 0.97/0.94). Shift up as top card exits.
- **Duration:** 0.3s ease-out (shift on card exit)
- **Purpose:** Gives the deck physicality — you see what's coming

### Shard & Reward Feedback

#### Animation 5: Shard Burst
- **Trigger:** DOWN swipe (synthesize)
- **Effect:** Shard icons explode outward from card center, arc toward their ShardBar counter (particle trajectory)
- **Duration:** 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)
- **Purpose:** Replaces the subtle float-up. Shards should *fly to their counter*.

#### Animation 6: Shard Counter Bump
- **Trigger:** ShardBar counter receives shards (after Shard Burst lands)
- **Effect:** Specific counter does scale bump 1.0 → 1.3 → 1.0 with brief orange background flash
- **Duration:** 0.2s ease-out
- **Purpose:** Confirms the reward landed

#### Animation 7: Combo Multiplier Flash
- **Trigger:** Consecutive DOWN swipes of same card type
- **Effect:** "x2", "x3" text scales up from card center and fades out upward
- **Duration:** 0.5s ease-out
- **Purpose:** Rewards streaky play patterns (visual only — no gameplay change unless combo mechanic exists)

### Powerups

#### Animation 8: Powerup Activation Burst
- **Trigger:** Powerup is used
- **Effect:** Radial shockwave ring expands from the powerup button. Color matches powerup type.
- **Duration:** 0.5s ease-out, opacity fades
- **Purpose:** Makes powerup use feel impactful

#### Animation 9: Powerup Panel Slide
- **Trigger:** PowerupPanel opens
- **Effect:** Panel slides up from bottom with overshoot bounce
- **Duration:** 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)
- **Purpose:** Replaces instant appear with physical weight

#### Animation 10: Reroll Spin
- **Trigger:** REROLL powerup activated
- **Effect:** Current card does rapid 360° spin (rotateY), then replaced with new card via Card Flip Entrance
- **Duration:** 0.4s ease-in-out
- **Purpose:** Visual feedback that the deck was shuffled

### Quiz & Stage Progression

#### Animation 11: Quiz Timer Pulse
- **Trigger:** Quiz timer enters last 5 seconds
- **Effect:** Timer ring pulses red, frequency increases as time runs out (2s → 1s → 0.5s intervals)
- **Duration:** Continuous until timer ends
- **Purpose:** Creates urgency, raises tension

#### Animation 12: Quiz Correct Celebration
- **Trigger:** Correct quiz answer
- **Effect:** Green flash overlay (0.1s) + shard burst toward ShardBar + brief screen shake (2px, 3 cycles)
- **Duration:** 0.5s total
- **Purpose:** Feels earned — multi-sensory positive feedback

#### Animation 13: Quiz Wrong Feedback
- **Trigger:** Wrong quiz answer
- **Effect:** Red flash overlay (0.1s) + card shudder (horizontal shake 3px, 3 cycles)
- **Duration:** 0.3s ease-out
- **Purpose:** Clear negative feedback without being punishing

#### Animation 14: Stage Complete Banner
- **Trigger:** All cards in a stage completed
- **Effect:** "STAGE X COMPLETE" text slams in from top (translateY(-100%) → 0 with scale overshoot 1.0 → 1.1 → 1.0), holds 1.5s, exits upward
- **Duration:** 0.4s enter + 1.5s hold + 0.3s exit
- **Purpose:** Fighting-game round announcement feel. Punctuates progression.

### Milestones & Progression

#### Animation 15: Milestone Unlock
- **Trigger:** Player hits a milestone threshold
- **Effect:** Brief full-screen white flash (0.1s) + milestone badge scales 0 → 1.2 → 1.0 + gold particle ring expands outward
- **Duration:** 0.8s total
- **Purpose:** Achievement moment. Should feel like unlocking something special.

#### Animation 16: Streak Fire
- **Trigger:** Streak counter ≥ 3 (on ProfilePage)
- **Effect:** Streak number gets looping orange glow pulse (box-shadow oscillates between subtle and bright orange)
- **Duration:** 1.5s infinite ease-in-out
- **Purpose:** Rewards consistency. Visual badge of honor.

#### Animation 17: Collection Discovery
- **Trigger:** New card discovered (first time seen in CollectionBook)
- **Effect:** Card slot transitions from "???" to revealed card with left-to-right wipe (clip-path reveal)
- **Duration:** 0.4s ease-out
- **Purpose:** Discovery moment in the collection grid

### Navigation & Page Transitions

#### Animation 18: Page Slide Transitions
- **Trigger:** Tab change in BottomNav
- **Effect:** Pages slide horizontally (left/right based on tab index position). Outgoing page exits opposite direction.
- **Duration:** 0.25s ease-out
- **Purpose:** Spatial navigation — tabs have physical positions

#### Animation 19: BottomNav Active Indicator
- **Trigger:** Active tab changes
- **Effect:** Thick orange underline slides between tabs (translateX transition)
- **Duration:** 0.2s ease-out
- **Purpose:** Replaces static color swap with physical movement

### Ambient

#### Animation 20: Idle Card Breathe
- **Trigger:** No user input for 3 seconds
- **Effect:** Current card does very subtle scale pulse 1.0 → 1.01 → 1.0
- **Duration:** 3s infinite ease-in-out
- **Purpose:** The game is alive, waiting for you. Subtle "pick me up" cue.

---

## Implementation Notes

- **CSS-first approach:** All animations defined as CSS keyframes/transitions in `index.css`. No JavaScript animation libraries needed.
- **Tailwind utilities:** Add custom animation utilities to `tailwind.config.js` for reuse.
- **Scanline overlay:** Pure CSS using `repeating-linear-gradient` on a `::after` pseudo-element. No image assets.
- **3D card flip:** Uses `transform-style: preserve-3d` and `backface-visibility: hidden` — widely supported.
- **Shard burst particles:** Lightweight CSS-only approach using multiple `::before`/`::after` elements with different animation delays, or a small set of absolutely-positioned shard icons.
- **Page transitions:** Wrap routes in a transition container with CSS classes toggled on navigation. No external router animation library needed.
- **Performance:** All animations use `transform` and `opacity` only (GPU-composited). No layout-triggering properties animated.

## Testing Considerations

- All animations must be disabled when `prefers-reduced-motion: reduce` is set
- Swipe interactions must remain responsive during animations (no blocking)
- Page transitions should not delay navigation or cause layout shifts
- E2E tests should verify game flow still works with animations enabled
- Visual regression snapshots for key states (card display, quiz, collection grid)

## Files Affected

- `frontends/sastahero/src/index.css` — All keyframes, scanline overlay, brutalist utility classes
- `frontends/sastahero/tailwind.config.js` — Animation utilities, updated theme tokens
- `frontends/sastahero/src/components/CardDisplay.jsx` — Card flip, stack depth, scanline overlay
- `frontends/sastahero/src/components/CardFeed.jsx` — Page transition wrapper
- `frontends/sastahero/src/components/SwipeHandler.jsx` — Swipe trail, label pop, idle breathe
- `frontends/sastahero/src/components/ShardBar.jsx` — Shard burst target, counter bump
- `frontends/sastahero/src/components/QuizCard.jsx` — Timer pulse, correct/wrong feedback
- `frontends/sastahero/src/components/PowerupPanel.jsx` — Panel slide, activation burst, reroll spin
- `frontends/sastahero/src/components/MilestonePopup.jsx` — Milestone unlock animation
- `frontends/sastahero/src/components/BottomNav.jsx` — Brutalist restyle, sliding indicator
- `frontends/sastahero/src/pages/GameFeed.jsx` — Stage complete banner
- `frontends/sastahero/src/pages/CollectionBook.jsx` — Discovery reveal, dense grid, brutal borders
- `frontends/sastahero/src/pages/StoryThread.jsx` — Terminal-style narrative
- `frontends/sastahero/src/pages/KnowledgeBank.jsx` — Fact blocks, pill filters
- `frontends/sastahero/src/pages/ProfilePage.jsx` — Stats HUD, streak fire
- `frontends/sastahero/src/App.jsx` — Route transition wrapper
