# SastaHero Implementation Plan

## Overview

This plan transforms the existing SastaHero RPG character builder into the endless-scrolling card game described in the [Game Design Spec](./2026-03-19-sastahero-game-design.md). The existing backend module and frontend will be **fully rewritten**. Infrastructure (Docker, Traefik, routing) stays unchanged.

**Estimated phases:** 7 phases, each independently deployable and testable.

---

## Phase 0: Scaffolding & Data Foundation

**Goal:** Strip old code, set up new data models, seed the card/content database.

### 0.1 — Backend: New Models & Schemas

**Files to rewrite:**
- `backend/app/modules/sastahero/schemas.py`
- `backend/app/modules/sastahero/models.py` (new)
- `backend/app/modules/sastahero/services.py`
- `backend/app/modules/sastahero/router.py`

**New Pydantic models / MongoDB document shapes:**

```
CardType          — Enum: CREATION, PROTECTION, DESTRUCTION, ENERGY, POWER
RarityTier        — Enum: COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
ContentType       — Enum: STORY, KNOWLEDGE, RESOURCE
SwipeAction       — Enum: UP (play), DOWN (synthesize), RIGHT (save), LEFT (share)
ShardType         — Enum: SOUL, SHIELD, VOID, LIGHT, FORCE
PowerupType       — Enum: REROLL, PEEK, MAGNETIZE, FUSION_BOOST, QUIZ_SHIELD, LUCKY_DRAW

CardIdentity      — id, name, types: list[CardType], rarity: RarityTier, shard_yield: int
CardVariant       — identity_id, content_type: ContentType, text: str, category?: str
CardInstance      — variant ref + identity ref, rendered for a specific stage

PlayerDocument    — player_id (UUID), shards: dict[ShardType, int], collection: list[str],
                    streak: {count, last_played_date}, stages_completed: int,
                    active_powerups: list, badges: list, created_at, updated_at

PlayerDeck        — player_id, stage_number, cards: list[CardInstance],
                    swipe_history: list[{card_index, action, timestamp}],
                    completed: bool

CommunityPoolEntry — identity_id, share_count, expires_at (TTL indexed)

StoryThread       — player_id, chapters: list[{number, fragments: list[str], created_at}],
                    current_fragments: list[str]

KnowledgeBankEntry — player_id, fact_id, category, text, saved_at

QuizQuestion      — id, question, options: list[str], correct_index, category, difficulty
Fact              — id, text, category, tags: list[str]
```

### 0.2 — Seed Data

**New files:**
- `backend/app/modules/sastahero/seed/` directory
  - `cards.json` — 31 card identities (5 common + 10 uncommon + 10 rare + 5 epic + 1 legendary)
  - `card_variants.json` — ~100 content variants across identities (~3 per identity avg)
  - `facts.json` — ~500 curated facts (start with ~50 for MVP, expand)
  - `quiz_questions.json` — ~200 quiz questions (start with ~30 for MVP, expand)
- `backend/app/modules/sastahero/seed/seeder.py` — Script to load seed data into MongoDB

**Card identity design (all 31):**

| Rarity | Combinations | Count |
|--------|-------------|-------|
| Common | C, P, D, E, Pw | 5 |
| Uncommon | C+P, C+D, C+E, C+Pw, P+D, P+E, P+Pw, D+E, D+Pw, E+Pw | 10 |
| Rare | C+P+D, C+P+E, C+P+Pw, C+D+E, C+D+Pw, C+E+Pw, P+D+E, P+D+Pw, P+E+Pw, D+E+Pw | 10 |
| Epic | C+P+D+E, C+P+D+Pw, C+P+E+Pw, C+D+E+Pw, P+D+E+Pw | 5 |
| Legendary | C+P+D+E+Pw | 1 |

Each identity gets a name (e.g., "Rebirth" for C+D, "Singularity" for all 5).

### 0.3 — Database Setup

- Create MongoDB indexes:
  - `card_pool.expires_at` — TTL index for community pool decay
  - `players.player_id` — unique index
  - `player_decks.player_id` + `player_decks.stage_number` — compound index
  - `knowledge_bank.player_id` — index
  - `story_threads.player_id` — unique index
- Add DB initialization to `backend/app/db/` or module startup

### 0.4 — Backend Tests for Phase 0

- `backend/tests/test_sastahero/` (convert to package for better organization)
  - `test_schemas.py` — Validate all Pydantic models serialize/deserialize correctly
  - `test_seed_data.py` — Validate seed JSON files load and match schema expectations

### 0.5 — Frontend: Strip Old Code

- Remove all old components: `ClassSelector`, `StatAllocator`, `HeroCard`, `RandomizeButton`, `ExportButton`
- Remove old store: `useHeroStore.js`
- Remove old page: `HeroBuilder.jsx`
- Keep: `App.jsx` (update routes), `main.jsx`, `index.css`, config files
- Remove `html-to-image` dependency from `package.json`
- Add `react-swipeable` dependency

**Quality gate:** `make ci-fast` passes with stripped frontend (blank app renders) and new backend models.

---

## Phase 1: Core Card Feed & Swipe Mechanics

**Goal:** Player can open the game, see cards, and swipe in 4 directions. No persistence yet.

### 1.1 — Backend: Stage Generation Endpoint

**`GET /api/v1/sastahero/stage`**

Query params: `player_id` (UUID string)

Logic:
1. Look up player (create if not exists with empty state)
2. Generate 10 cards:
   - Roll rarity per card using drop rates (60% common, 25% uncommon, 10% rare, 4% epic, 1% legendary)
   - Pick random identity of that rarity
   - Pick random content variant for that identity
   - Mix content types: ~5 story, ~3 knowledge, ~2 resource (shuffle after assignment)
   - Check community pool — boost drop rate for high-share-count identities
   - Avoid exact duplicate identities within same stage
3. Create `PlayerDeck` document
4. Return list of card objects (with id, name, types, rarity, content_type, text, shard_yield)

**Services:**
- `generate_stage(player_id: str) -> list[CardInstance]`
- `_roll_rarity() -> RarityTier`
- `_pick_identity(rarity: RarityTier, exclude: set[str]) -> CardIdentity`
- `_pick_variant(identity_id: str) -> CardVariant`
- `_apply_community_pool_boost(base_rates: dict) -> dict`

### 1.2 — Backend: Swipe Processing Endpoint

**`POST /api/v1/sastahero/swipe`**

Body: `{ player_id, card_id, action: SwipeAction }`

Logic per action:
- **UP (play):** Add card to story thread fragments. Mark in collection if first encounter.
- **DOWN (synthesize):** Award shards based on card types × shard_yield.
- **RIGHT (save):** Add to collection. If knowledge card, add to knowledge bank.
- **LEFT (share):** Add/increment community pool entry (set expires_at = now + 48h). Award 1 random shard.

Return: `{ shards: dict, collection_updated: bool, new_items: list }`

### 1.3 — Frontend: Card Feed UI

**New components:**
- `src/components/CardFeed.jsx` — Full-screen vertical card container, manages current card index
- `src/components/CardDisplay.jsx` — Single card rendering:
  - CSS gradient background based on card types (gold, blue, red, white, purple)
  - Rarity glow border (subtle → intense)
  - Type badge(s), rarity label
  - Content text
  - Shard yield indicator
  - Card count indicator: "3/10"
- `src/components/SwipeHandler.jsx` — Wraps CardDisplay, detects 4-direction swipes
  - Uses `react-swipeable` for touch
  - Mouse drag fallback for desktop
  - Swipe direction indicator animation (arrow + action label)
  - Threshold: 50px minimum drag

**New store:**
- `src/store/useGameStore.js` (Zustand)
  - State: `playerId`, `cards[]`, `currentIndex`, `shards{}`, `stageNumber`, `isLoading`
  - Actions: `fetchStage()`, `processSwipe(direction)`, `initPlayer()`

**New page:**
- `src/pages/GameFeed.jsx` — Main game screen
  - On mount: init player (generate UUID if none in localStorage), fetch first stage
  - Renders ShardBar + CardFeed
  - After 10 swipes: transition to quiz (Phase 2) or next stage

**Update:**
- `src/App.jsx` — Route "/" → GameFeed

### 1.4 — Frontend: Shard Bar

- `src/components/ShardBar.jsx` — Persistent top bar
  - 5 shard types with icons and counts
  - Color-coded to match card types
  - Compact on mobile, expanded on desktop
  - Animates on shard gain

### 1.5 — Tests

**Backend:**
- `test_stage_generation.py`:
  - Returns exactly 10 cards
  - Content type distribution roughly matches (5/3/2)
  - No duplicate identities in single stage
  - Rarity distribution is within expected range over many rolls
  - Creates player if not exists
  - Creates player_deck document

- `test_swipe_processing.py`:
  - UP: card added to story fragments, collection updated
  - DOWN: correct shard types and amounts awarded
  - RIGHT: card added to collection, knowledge card saved to bank
  - LEFT: community pool entry created/incremented, 1 shard awarded
  - Invalid card_id returns 404
  - Invalid action returns 422

**Frontend:**
- `CardDisplay.test.jsx` — Renders card with correct type colors, rarity, content
- `SwipeHandler.test.jsx` — Fire touch/mouse events, verify correct direction detected
- `CardFeed.test.jsx` — Advances through cards on swipe
- `ShardBar.test.jsx` — Shows correct shard counts, updates on change
- `GameFeed.test.jsx` — Loads stage on mount, processes swipes

**Quality gate:** `make ci-fast` passes. Player can open game, see 10 cards, swipe all 4 directions, see shard counts update.

---

## Phase 2: Quiz System

**Goal:** Quiz appears between stages. Correct answers award bonuses.

### 2.1 — Backend: Quiz Endpoints

**`GET /api/v1/sastahero/quiz`**
- Query: `player_id`
- Select a quiz question the player hasn't seen recently
- Prefer questions from categories matching recently-seen knowledge cards
- Return: `{ question_id, question, options: [4 strings], time_limit: 15 }`

**`POST /api/v1/sastahero/quiz/answer`**
- Body: `{ player_id, question_id, selected_index, time_taken_ms }`
- Check correctness, calculate rewards:
  - Correct + fast (<5s): 3 shards + flag for guaranteed uncommon next stage
  - Correct + normal: 2 shards
  - Wrong: 1 consolation shard
- Track streak (3 correct in a row = rare card next stage)
- Return: `{ correct: bool, correct_index, reward_shards, streak_count, bonus_card: bool }`

### 2.2 — Frontend: Quiz UI

**New components:**
- `src/components/QuizCard.jsx`:
  - Full-screen quiz display
  - Question text, 4 option buttons
  - 15-second countdown timer (animated ring)
  - Tap to answer, instant feedback (green/red highlight)
  - Show correct answer if wrong
  - Reward summary before proceeding
- `src/components/QuizTimer.jsx` — Circular countdown, triggers auto-submit on expiry

**Store updates:**
- `useGameStore.js`: Add `quizState`, `quizStreak`, `showQuiz`, `submitQuizAnswer()`

**Flow update in GameFeed:**
- After 10 swipes → show QuizCard → on answer → fetch next stage → continue

### 2.3 — Tests

**Backend:**
- `test_quiz.py`:
  - Returns valid question with 4 options
  - Correct answer with fast time returns 3 shards
  - Correct answer returns 2 shards
  - Wrong answer returns 1 shard + correct_index
  - Streak tracking (3 correct = bonus)
  - Doesn't repeat recently-seen questions

**Frontend:**
- `QuizCard.test.jsx` — Renders question and options, handles answer selection
- `QuizTimer.test.jsx` — Countdown works, triggers callback on expiry

**Quality gate:** `make ci-fast` passes. Full loop works: 10 cards → quiz → 10 cards → quiz...

---

## Phase 3: Player State & Collection

**Goal:** Persistent player identity, collection book, shards, streaks.

### 3.1 — Backend: Player & Collection Endpoints

**`GET /api/v1/sastahero/collection`**
- Query: `player_id`
- Return: All 31 card identities with `discovered: bool` for each
- Completion stats: `{ discovered: 19, total: 31, by_rarity: { common: 5/5, uncommon: 7/10, ... } }`

**`GET /api/v1/sastahero/shards`**
- Query: `player_id`
- Return: `{ soul: 12, shield: 8, void: 5, light: 14, force: 3 }`

**`GET /api/v1/sastahero/profile`**
- Query: `player_id`
- Return: `{ stages_completed, streak: { count, last_played }, badges: [], community_score, cards_shared, collection_pct }`

### 3.2 — Backend: Streak Logic

- On each `GET /stage`: check `last_played_date`
  - Same day: no change
  - Yesterday: increment streak
  - Older: reset to 1
- Streak rewards applied when generating stage:
  - Day 3: inject 1 rare card into stage
  - Day 7: inject 1 epic card
  - Day 14: flag for guaranteed legendary within next 5 stages

### 3.3 — Backend: Milestone Tracking

- After processing stage completion, check `stages_completed`:
  - 5 stages: award 5 random shards
  - 10 stages: inject guaranteed rare next stage
  - 25 stages: award badge + epic card
  - 50 stages: flag legendary next stage
  - 100 stages: award title + all-shard bonus

### 3.4 — Frontend: Collection Book

**New component:**
- `src/components/CollectionBook.jsx`:
  - Grid of 31 card identity slots
  - Discovered cards show full art/name/type
  - Undiscovered show silhouette/question mark
  - Filter by rarity tier
  - Completion percentage header
  - Rarity tier badges (unlocked when tier fully discovered)

### 3.5 — Frontend: Profile Page

**New component:**
- `src/pages/ProfilePage.jsx`:
  - Streak counter with flame icon
  - Stages completed
  - Collection completion %
  - Badges earned
  - Community score (cards shared, impact)
  - Shard totals

### 3.6 — Frontend: Milestone Popup

- `src/components/MilestonePopup.jsx`:
  - Celebration overlay on milestone hit
  - Shows reward earned
  - Auto-dismiss after 3 seconds or tap

### 3.7 — Frontend: Navigation

- Update `App.jsx` with routes:
  - `/` → GameFeed
  - `/collection` → CollectionBook
  - `/profile` → ProfilePage
- Bottom navigation bar with 3 tabs: Play, Collection, Profile

### 3.8 — Tests

**Backend:**
- `test_collection.py` — Returns all 31 identities, marks discovered correctly
- `test_profile.py` — Stats accurate, streak calculation correct
- `test_milestones.py` — Rewards trigger at correct thresholds

**Frontend:**
- `CollectionBook.test.jsx` — Renders grid, shows discovered/undiscovered states
- `ProfilePage.test.jsx` — Displays streak, stats, badges
- `MilestonePopup.test.jsx` — Shows/hides with correct reward text

**Quality gate:** `make ci-fast` passes. Player state persists across sessions via localStorage player_id.

---

## Phase 4: Powerup System

**Goal:** Players can spend shards on powerups that modify gameplay.

### 4.1 — Backend: Powerup Endpoint

**`POST /api/v1/sastahero/powerup`**
- Body: `{ player_id, powerup_type: PowerupType }`
- Validate shard balance meets cost:
  - REROLL: 3 of any single type
  - PEEK: 2 of any single type
  - MAGNETIZE: 5 of one type (must specify which)
  - FUSION_BOOST: 1 of each type (5 total)
  - QUIZ_SHIELD: 4 of any single type
  - LUCKY_DRAW: 3 of 3 different types
- Deduct shards, add powerup to player's `active_powerups`
- Return: updated shard balances + active powerups list

### 4.2 — Backend: Powerup Effects in Stage Generation

Modify `generate_stage()`:
- **REROLL:** Not stage-gen; separate endpoint `POST /api/v1/sastahero/reroll` replaces current card
- **PEEK:** Return next 3 cards as preview alongside current card
- **MAGNETIZE:** Override stage generation to include 3+ cards of specified type
- **FUSION_BOOST:** Double combo card (uncommon+) drop rates for 2 stages (tracked in player state)
- **QUIZ_SHIELD:** Flag on player, consumed on next wrong quiz answer (allows re-answer)
- **LUCKY_DRAW:** Force one rare+ card into next stage

### 4.3 — Frontend: Powerup Panel

**New components:**
- `src/components/PowerupPanel.jsx`:
  - Slide-up panel from bottom of GameFeed
  - Grid of 6 powerups with icons, names, costs
  - Greyed out if insufficient shards
  - Tap to purchase, confirmation, shard animation
- `src/components/PowerupButton.jsx` — Floating action button on GameFeed to open panel
- `src/components/PeekOverlay.jsx` — Shows next 3 cards when Peek is active

**Store updates:**
- `useGameStore.js`: Add `activePowerups`, `purchasePowerup()`, `useReroll()`, `peekCards`

### 4.4 — Tests

**Backend:**
- `test_powerups.py`:
  - Purchase succeeds with sufficient shards
  - Purchase fails with insufficient shards (400 error)
  - Each powerup type deducts correct shard cost
  - Powerup effects apply correctly in stage generation
  - Reroll replaces current card
  - Used powerups consumed from active list

**Frontend:**
- `PowerupPanel.test.jsx` — Shows all powerups, disables when unaffordable
- Purchase flow test — shards deducted, powerup activated

**Quality gate:** `make ci-fast` passes. Players can buy and use all 6 powerups.

---

## Phase 5: Story Thread & Knowledge Bank

**Goal:** Played cards build a story. Saved knowledge cards create a browsable learning journal.

### 5.1 — Backend: Story Endpoints

**`GET /api/v1/sastahero/story`**
- Query: `player_id`
- Return: `{ chapters: [{ number, text, card_count, created_at }], current_fragments: [], total_chapters }`

**Story logic (in swipe processing for UP action):**
- Append card's story fragment to `current_fragments`
- Every 10 played cards: concatenate fragments into a chapter, push to `chapters` array, clear `current_fragments`

### 5.2 — Backend: Knowledge Endpoints

**`GET /api/v1/sastahero/knowledge`**
- Query: `player_id`, optional `category` filter
- Return: `{ facts: [{ text, category, saved_at }], categories: [distinct list], total }`

### 5.3 — Frontend: Story Thread Page

**New component:**
- `src/pages/StoryThread.jsx`:
  - Scrollable list of chapters
  - Each chapter shows number, concatenated text, date
  - Current in-progress fragments shown at top
  - Empty state for new players

### 5.4 — Frontend: Knowledge Bank Page

**New component:**
- `src/pages/KnowledgeBank.jsx`:
  - List of saved facts
  - Filter by category (tabs or dropdown)
  - Search within saved facts
  - Count per category
  - Empty state for new players

### 5.5 — Navigation Update

- Update bottom nav: Play | Collection | Story | Knowledge | Profile
- Or use a hamburger menu for Story/Knowledge/Profile and keep bottom nav minimal: Play | Collection | Me

### 5.6 — Tests

**Backend:**
- `test_story.py` — Chapters created every 10 played cards, fragments concatenate
- `test_knowledge.py` — Facts saved correctly, category filter works

**Frontend:**
- `StoryThread.test.jsx` — Renders chapters, shows empty state
- `KnowledgeBank.test.jsx` — Renders facts, filters by category

**Quality gate:** `make ci-fast` passes.

---

## Phase 6: Community Pool & Optimistic UI

**Goal:** Sharing works globally. Swipe flow feels instant.

### 6.1 — Backend: Community Pool

Already partially implemented in Phase 1 swipe processing (LEFT action). Enhance:

- `card_pool` collection with TTL index on `expires_at`
- On share: upsert with `$inc: { share_count: 1 }`, set `expires_at = now + 48h`
- On interact (play/save a pool card): `$set: { expires_at: now + 12h }` (extend)
- Stage generation queries pool and boosts drop rates for high-share cards
- Profile endpoint returns `cards_shared` and `community_score`

### 6.2 — Frontend: Community Indicators

- On each card in feed: show small counter "47 players have this" (from pool data)
- Profile page: community contribution stats

### 6.3 — Frontend: Optimistic UI

**Store refactor in `useGameStore.js`:**
- Swipe updates local state immediately (shards, collection, story)
- Fire `POST /swipe` in background
- Queue failed requests for retry (up to 3 attempts)
- Batch swipe events: if player swipes faster than network, accumulate and send at stage end
- `GET /stage` response includes authoritative state — reconcile any drift

**Implementation:**
- Add `pendingSwipes: []` to store
- `processSwipe()` updates local state + pushes to queue
- Background effect flushes queue periodically or on stage end
- `fetchStage()` response overwrites shards/collection with server truth

### 6.4 — Frontend: Session Design

- After every 2-3 stages, show gentle break suggestion:
  - "Nice session! You discovered 2 new cards and learned 3 facts. See you later?"
  - "Continue" or "Take a break" buttons
  - No penalty for continuing — just a healthy nudge

### 6.5 — Tests

**Backend:**
- `test_community_pool.py`:
  - Share creates pool entry with correct TTL
  - Repeated shares increment count
  - Interaction extends TTL
  - Stage gen boosts pool cards

**Frontend:**
- Optimistic UI tests — local state updates before network response
- Queue/retry tests — failed swipes queued and retried
- Reconciliation test — server state overwrites on stage fetch

**Quality gate:** `make ci-fast` passes. Full game loop works end-to-end with optimistic UI.

---

## Phase 7: Polish & Content Expansion

**Goal:** Visual polish, animations, accessibility, and content scaling.

### 7.1 — Card Visuals

- CSS mesh gradient backgrounds per card type (animated)
- Rarity glow borders (CSS box-shadow animations)
- Swipe direction animations (card slides off screen in swipe direction)
- Card flip animation on reveal
- Type icons (simple SVG glyphs): ✦ Creation, ◆ Protection, ✕ Destruction, ☀ Energy, ⬟ Power

### 7.2 — Animations & Transitions

- Shard gain: floating +N animation on ShardBar
- Milestone popup: confetti/particle effect (CSS only)
- Quiz timer: pulsing ring animation
- Page transitions: slide between tabs

### 7.3 — Mobile Optimization

- Viewport meta tag (already in index.html)
- Touch feedback (haptic vibration API where available)
- Prevent pull-to-refresh during swipes (CSS `overscroll-behavior`)
- Safe area insets for notched phones

### 7.4 — Content Expansion

- Expand seed data to full MVP targets:
  - 100 card variants (from ~50)
  - 500 facts (from ~50)
  - 200 quiz questions (from ~30)
- Review and balance story fragments for coherent concatenation

### 7.5 — Accessibility

- ARIA labels on all interactive elements
- Keyboard navigation for desktop (arrow keys for swipes)
- Reduced motion media query support
- Color contrast compliance (brutalist aesthetic helps here)

### 7.6 — Final Tests & Quality

- Full E2E tests with Playwright (`make test-e2e-sastahero`)
- Coverage target: 66%+ (per CLAUDE.md)
- Performance audit: Lighthouse score
- `make ci-fast` green

---

## Implementation Order Summary

| Phase | What | Dependencies | Key Deliverable |
|-------|------|-------------|-----------------|
| **0** | Scaffolding & Data | None | Models, seed data, stripped frontend |
| **1** | Card Feed & Swipes | Phase 0 | Playable card swiping with shard tracking |
| **2** | Quiz System | Phase 1 | Quiz between stages, rewards |
| **3** | Player State | Phase 1-2 | Collection book, profile, streaks, milestones |
| **4** | Powerups | Phase 1, 3 | 6 purchasable powerups |
| **5** | Story & Knowledge | Phase 1-2 | Story chapters, knowledge bank |
| **6** | Community & Optimistic UI | Phase 1, 3 | Sharing pool, instant swipe feel |
| **7** | Polish | All above | Animations, content, a11y, E2E |

## File Impact Summary

### Backend — New/Rewritten Files
```
backend/app/modules/sastahero/
├── __init__.py                    (keep)
├── schemas.py                     (full rewrite — card models, player models, etc.)
├── models.py                      (new — MongoDB document shapes)
├── services.py                    (full rewrite — stage gen, swipe, quiz, powerups)
├── router.py                      (full rewrite — 10 endpoints)
├── constants.py                   (new — card names, drop rates, shard costs)
└── seed/
    ├── __init__.py
    ├── cards.json
    ├── card_variants.json
    ├── facts.json
    ├── quiz_questions.json
    └── seeder.py

backend/tests/
├── test_sastahero.py              (full rewrite or split into package)
└── test_sastahero/                (alternative: test package)
    ├── __init__.py
    ├── test_schemas.py
    ├── test_stage_generation.py
    ├── test_swipe_processing.py
    ├── test_quiz.py
    ├── test_collection.py
    ├── test_profile.py
    ├── test_powerups.py
    ├── test_story.py
    ├── test_knowledge.py
    └── test_community_pool.py
```

### Frontend — New/Rewritten Files
```
frontends/sastahero/src/
├── main.jsx                       (keep)
├── App.jsx                        (rewrite routes)
├── index.css                      (extend with card gradients)
├── store/
│   └── useGameStore.js            (new — replaces useHeroStore.js)
├── pages/
│   ├── GameFeed.jsx               (new — replaces HeroBuilder.jsx)
│   ├── CollectionBook.jsx         (new)
│   ├── StoryThread.jsx            (new)
│   ├── KnowledgeBank.jsx          (new)
│   └── ProfilePage.jsx            (new)
├── components/
│   ├── CardFeed.jsx               (new)
│   ├── CardDisplay.jsx            (new)
│   ├── SwipeHandler.jsx           (new)
│   ├── ShardBar.jsx               (new)
│   ├── QuizCard.jsx               (new)
│   ├── QuizTimer.jsx              (new)
│   ├── PowerupPanel.jsx           (new)
│   ├── PowerupButton.jsx          (new)
│   ├── PeekOverlay.jsx            (new)
│   ├── MilestonePopup.jsx         (new)
│   ├── BottomNav.jsx              (new)
│   └── BreakSuggestion.jsx        (new)
└── test/
    └── setup.js                   (keep)

Removed files:
  - src/store/useHeroStore.js
  - src/pages/HeroBuilder.jsx
  - src/components/ClassSelector.jsx
  - src/components/StatAllocator.jsx
  - src/components/HeroCard.jsx
  - src/components/RandomizeButton.jsx
  - src/components/ExportButton.jsx
  + their test files
```

### Infrastructure — No Changes
- `docker-compose.yml` — unchanged
- `Dockerfile` — unchanged
- `nginx.conf` — unchanged
- `vite.config.js` — unchanged (base path `/sastahero/` stays)
- `tailwind.config.js` — extend with new card colors (minor update)

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Seed data quality (story fragments don't concatenate well) | Author fragments in pairs/groups that are designed to work together |
| Community pool empty for single player | Stage gen works without pool; pool just boosts rates |
| Optimistic UI drift | Stage-end reconciliation is authoritative; test drift scenarios |
| Mobile swipe conflicts with browser gestures | `overscroll-behavior: none`, `touch-action: none` on card area |
| Test coverage regression | Run `make ci-fast` after every phase |

## Definition of Done (per Phase)

1. All new endpoints return correct responses
2. All new components render correctly
3. Backend + frontend tests pass
4. `make ci-fast` passes (lint, typecheck, complexity, coverage, all tests)
5. Game loop works end-to-end for the features in that phase
