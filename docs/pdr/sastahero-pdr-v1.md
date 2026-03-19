# SastaHero -- Product Design Review (PDR)
# Version: 1.0
# Date: 2026-03-19
# Author: AI Game Director
# Status: APPROVED FOR EXECUTION

---

## 1. EXECUTIVE SUMMARY

SastaHero is an endless-scrolling card game designed to replace doom-scrolling with meaningful 3-5 minute micro-sessions. Players swipe through full-screen cards in four directions (play, synthesize, save, share), building a collection of 31 unique card identities across 5 rarity tiers, answering quiz questions between stages, accumulating a personal story thread, and banking real knowledge. The target audience is 16-30 year olds who lose 30-60 minutes daily to TikTok/Instagram and feel guilty about it. SastaHero will succeed because it occupies a genuinely uncontested market position: "productive doom-scrolling" -- the exact same swipe mechanic and variable-ratio dopamine loop, but every session deposits something real into the player's brain. No other product in the App Store occupies this niche with a game-native approach.

**Market positioning**: SastaHero is not a learning app gamified (Duolingo) or a game with trivia (Trivia Crack). It is a genuine card collector with a knowledge bank as the anti-addiction payoff -- the first game that gets better for the player the more they put it down.

**Marketing hook**: "Everything TikTok gives you, except you keep something."

**Target app store rating**: 4.6+ (achievable -- anti-addiction framing deflects the "too addictive" 1-star reviews that plague gacha games)

**Target DAU/MAU ratio**: 0.35 (strong for casual -- Candy Crush runs 0.30, Wordle peaked at 0.45; our short sessions and streak system push daily habit)

**Target retention (D1/D7/D30)**: 55% / 30% / 15%. Justification: D1 is high because the zero-friction anonymous auth means no drop-off at registration. D7 depends on streak rewards kicking in at Day 3 and Day 7. D30 at 15% is realistic for a content-consumption game without social graph integration at launch. The streak Day 14 legendary guarantee is the D30 anchor.

---

## 2. COMPLETION SCORECARD

The card game implementation exists on feature branch `claude/game-implementation-plan-RZwYh` (commits `1ab25a7` through `3a88fd2`) and has NOT been merged into `main`. Main still contains the old RPG hero builder. All scores below reference the feature branch code.

| System | Score | Priority |
|--------|-------|----------|
| Core Game Loop (swipe -> stage -> quiz -> repeat) | 85% | P0 |
| Card Identity System (31 cards, types, rarities) | 95% | -- |
| Shard Economy (earn, spend, balance) | 80% | P1 |
| Powerup System (6 powerups, cost, activation) | 90% | P1 |
| Quiz System (questions, timer, streak rewards) | 75% | P0 |
| Collection Book (discovery, completion %) | 80% | P1 |
| Story Thread (fragments -> chapters, coherence) | 70% | P2 |
| Knowledge Bank (facts, categories, browsing) | 70% | P1 |
| Player Profile (stats, streaks, badges) | 75% | P1 |
| Community Pool (share -> pool -> decay -> discovery) | 60% | P2 |
| Sound Design (Web Audio synth, haptics) | 80% | P1 |
| Visual Polish (gradients, glows, animations) | 75% | P1 |
| Onboarding / FTUE | 5% | P0 |
| Session Pacing (break suggestions, session limits) | 50% | P0 |
| Offline Resilience (pending swipes, retry) | 30% | P1 |
| Accessibility (WCAG, screen readers, reduced motion) | 65% | P1 |
| Performance (load time, animation FPS, bundle size) | 60% | P1 |
| Test Coverage (backend + frontend + E2E) | 85% | P1 |
| Deployment Readiness (Docker, env config, CI) | 70% | P0 |
| Content Volume (card variants, quiz questions) | 25% | P0 |

**Details per system**:

**Core Game Loop (85%)**: Stage generation (`services.py:248-355`), swipe processing (`services.py:361-580`), quiz flow (`services.py:649-754`), and stage completion with milestones (`services.py:586-646`) are all implemented. Frontend flow in `GameFeed.jsx` orchestrates card display -> swipe -> stage complete celebration -> quiz -> next stage. Missing: the flow has no graceful handling of network failures mid-stage; `StageComplete` always shows before quiz with no skip option; there is no "empty state" when all cards are swiped but network is slow.

**Card Identity System (95%)**: All 31 identities defined in `constants.py` (lines 77-196). 5 common, 10 uncommon, 10 rare, 5 epic, 1 legendary. Correct combinatorial type assignments. Lookup maps by ID and rarity grouping implemented. Missing: no card "lore" text beyond the variant content (a flavor text field per identity would deepen collection appeal).

**Shard Economy (80%)**: Five shard types mapped to five card types (`constants.py:14-20`). Shard yields scale with rarity (1/2/3/5/10). Synthesis (swipe down) awards component shards. Share (swipe left) awards 1 random shard. Quiz rewards 1-3 shards. All implemented in `services.py`. Missing: no shard overflow protection; no "exchange" mechanic for converting between shard types; the economy skews heavily toward whichever shard type the player encounters most.

**Powerup System (90%)**: All 6 powerups implemented (`services.py:819-902`): Reroll (3 any), Peek (2 any), Magnetize (5 specific), Fusion Boost (1 each), Quiz Shield (4 any), Lucky Draw (3 of 3 different). Frontend `PowerupPanel.jsx` shows costs and affordability. Reroll endpoint exists at `/reroll`. Missing: Peek powerup has no frontend preview UI (the backend marks it as purchased but the frontend never shows the next 3 cards).

**Quiz System (75%)**: 30 quiz questions in `seed/quiz_data.py` across science, history, psychology, geography, language. Timer (15s), streak tracking, fast-answer bonus all implemented. Frontend `QuizCard.jsx` handles timer, options, result display. Missing: 30 questions is far too few -- players will see repeats within 2 sessions; no difficulty scaling; quiz shield powerup is purchased but never consumed on wrong answer (`services.py:733-735` has a `pass` placeholder).

**Collection Book (80%)**: `CollectionBook.jsx` renders all 31 identities with discovered/undiscovered state. Backend `get_collection` returns full list with discovery flags. Missing: no rarity filter UI on frontend despite the schema supporting it; no "tap to view details" on collected cards; no completion tier badges displayed.

**Story Thread (70%)**: Coherent chapter assembly implemented with arc position sorting and theme transitions (`services.py:92-138`). `FRAGMENT_ARC_POSITIONS` and `IDENTITY_NARRATIVE_THEMES` in `card_variants.py` provide narrative metadata. Chapters auto-generate every 10 played cards. Missing: `StoryThread.jsx` page exists but is a basic list -- no reading experience; the narrative quality depends entirely on having enough well-authored fragments (currently only ~3 story variants per identity = ~93 story fragments total, many of which are single sentence fragments that produce choppy chapters).

**Knowledge Bank (70%)**: Backend saves knowledge cards on right-swipe, queries by category, returns sorted by date. Frontend `KnowledgeBank.jsx` renders with category filter. Missing: no search; no "share fact" functionality; no visual distinction between categories; the 31 identities have roughly 1 knowledge variant each = ~31 unique facts, which is nowhere near the 500 target.

**Player Profile (75%)**: `ProfilePage.jsx` shows stages completed, streak info, badges, community score, collection percentage. Backend `get_profile` computes all stats. Missing: no profile picture/avatar system; no "title" display from milestone 100; badge display is just text strings, no visual badges.

**Community Pool (60%)**: Share action inserts into `card_pool` with TTL (`services.py:504-520`). Pool counts influence stage generation. TTL extension on interaction (`services.py:1022-1029`). Missing: no frontend visibility of pool state; the "47 players have this" counter shows in `CardDisplay.jsx` but only if `community_count > 0`; no "your shared cards" view on profile; no viral credit system (spec says sharer earns rare card after 10 plays by others -- not implemented).

**Sound Design (80%)**: Full Web Audio synthesizer in `soundEngine.js` (~230 lines). Procedural SFX for: swipe (4 directional tones), card draw, shard gain (per-type pitched), quiz correct/wrong/tick/urgent, milestone fanfare, combo, stage complete, powerup activation, button click, streak. Haptic vibration patterns. Mute toggle. Missing: no ambient background tone; no volume slider in UI (only toggle); sound priming requires first interaction which may confuse users.

**Visual Polish (75%)**: CSS mesh gradients per card type (5 animated gradient sets in `index.css`). Rarity glow borders (common through legendary intensity). Card enter/exit animations. Safe area insets for notched phones. Missing: no loading skeleton screens; no micro-animations on shard bar updates; the brutalist aesthetic works but needs more visual hierarchy on data-dense pages (Collection, Profile); no dark/light mode toggle.

**Onboarding / FTUE (5%)**: No tutorial, no welcome screen, no guided first swipe, no explanation of what the four directions do. The game drops the player into a stage cold. This is a launch blocker. The only affordance is the swipe direction indicator overlay during active drag (`SwipeHandler.jsx`).

**Session Pacing (50%)**: Break suggestion triggers every 3 stages (`useGameStore.js` tracks `sessionStages`). `BreakSuggestion.jsx` shows a dismissible overlay. Missing: no session timer; no daily session cap; no session summary (the spec calls for "You discovered 2 new cards and learned 3 facts" -- not implemented); break suggestion is trivially dismissible with no friction.

**Offline Resilience (30%)**: `pendingSwipes` array in Zustand store captures failed swipes. Optimistic UI updates shards before network confirmation. Missing: pending swipes are never retried (they accumulate in state but no retry logic exists); no offline detection banner; no queue drain on reconnect; no localStorage persistence of game state (if tab closes, all pending swipes are lost).

**Accessibility (65%)**: ARIA labels on cards, shard bar, quiz, nav tabs, swipe area. Keyboard navigation (arrow keys + WASD). `role="application"` on swipe handler. `prefers-reduced-motion` disables animations. `role="dialog"` on powerup panel. Missing: no skip-to-content landmark; color contrast on ENERGY cards (yellow on light background) likely fails WCAG AA; no focus trap in modal dialogs; screen reader flow through quiz timer is noisy.

**Performance (60%)**: No image assets (all CSS + text). Vite build should produce a small bundle. React 18 with Zustand is lightweight. Missing: no lazy loading of routes; no service worker; no bundle analysis; the `generate_stage` endpoint makes N+1 queries to `card_pool` per card; no database indexes specified anywhere.

**Test Coverage (85%)**: 90 backend tests (`test_sastahero.py`, 1641 lines) covering all endpoints, edge cases, streaks, milestones, powerups, quiz logic. Frontend has SwipeHandler tests (keyboard nav), CardDisplay tests, ShardBar tests, GameFeed tests. 26 Playwright E2E tests across 3 spec files. The commit message claims 97.31% backend coverage. Missing: no frontend store tests for `useGameStore.js`; no integration tests for the optimistic UI flow; E2E tests may not run without proper backend mock.

**Deployment Readiness (70%)**: Dockerfile uses multi-stage build (node build -> nginx). Docker Compose routes through Traefik. The Dockerfile at `b05ad5f` was fixed to use `npm install` instead of `npm ci`. Missing: the feature branch is not merged into main; no MongoDB index creation script; no health check endpoint for the card game (only the old `/api/v1/common/health`); no rate limiting on player-facing endpoints; no environment-specific configuration for the card game.

**Content Volume (25%)**: ~127 card variant entries (5 per identity average: 3 story + 1 knowledge + 1 resource). 30 quiz questions. The design spec targets 100 seed cards with 500 facts and 200 quiz questions. Current content would be exhausted in 3-4 sessions. This is a launch blocker.

### Overall Completion: 62%
### Launch Readiness: NOT READY

**Blockers**: (1) Feature branch not merged to main. (2) No FTUE/onboarding. (3) Content volume at 25% of target (30 quiz questions, ~31 unique facts). (4) Quiz shield powerup not functional. (5) Offline retry logic absent.

---

## 3. CRITICAL FIXES (P0 -- Launch Blockers)

### 3.1 Merge Feature Branch to Main

- **Issue**: The entire card game lives on `claude/game-implementation-plan-RZwYh` (3 commits ahead of main). Main still serves the old RPG builder.
- **Impact**: Nothing works in production. Zero users can play the card game.
- **Fix**: Rebase the feature branch onto current main (resolve any conflicts in docs/), squash-merge, and verify `make ci-fast` passes.
- **Effort**: S
- **Decision**: Squash merge into a single commit titled "feat(sastahero): rewrite as endless card game". Run full CI after merge.

### 3.2 First-Time User Experience (FTUE)

- **Issue**: No tutorial. Players land in a 10-card stage with no explanation of swipe directions, shard economy, or quiz flow.
- **Impact**: D1 retention will be 20-30% instead of target 55%. Players who do not understand the four swipe directions within 10 seconds will leave.
- **Fix**: Add a `TutorialOverlay.jsx` component that activates when `localStorage` has no `sastahero_tutorial_complete` flag. The tutorial is 4 cards: (1) "Swipe UP to Play -- adds to your story" (2) "Swipe DOWN to Synthesize -- earn shards" (3) "Swipe RIGHT to Save -- add to collection" (4) "Swipe LEFT to Share -- help other players". Each card uses the same `CardDisplay` component with a semi-transparent instruction overlay. After the 4th card, show "You're ready. Every stage is 10 cards, then a quiz. Go." Set the flag and load the first real stage. No skip button during the first ever session.
- **Effort**: M
- **Decision**: 4-card interactive tutorial, mandatory on first session only.

### 3.3 Content Volume Expansion

- **Issue**: 30 quiz questions and ~31 knowledge facts. Players will see repeats by session 2. The "anti-doom-scroll knowledge payoff" is the entire value proposition and it has 31 data points.
- **Impact**: The core differentiator is hollow. The knowledge bank will feel empty. Press reviewers will notice within 5 minutes.
- **Fix**: Expand content in `seed/quiz_data.py` and `seed/card_variants.py`:
  - Target: 150 quiz questions (5x current) across 6 categories (science, history, psychology, geography, language, technology).
  - Target: 155 card variants (5 per identity: 3 story fragments + 1 knowledge fact + 1 resource). Currently at ~127, but many story fragments are single clauses. Rewrite all story variants to be 1-2 complete sentences that read well when concatenated.
  - Target: 100 unique knowledge facts (currently ~31).
  - Add 3 new knowledge categories: space, music, sports.
- **Effort**: L (content authoring is time-intensive but mechanically simple)
- **Decision**: Prioritize quiz questions first (highest player-facing impact), then knowledge variants, then story fragment polish.

### 3.4 Quiz Shield Powerup Not Functional

- **Issue**: `services.py:733-735` detects the quiz shield but does nothing (`pass`). The player pays 4 shards for a powerup that has zero effect.
- **Impact**: Trust-destroying bug. Players who discover this will feel cheated and leave negative reviews.
- **Fix**: When `has_shield` is True and `correct` is False: set `correct = True`, set `reward_shards = 1` (consolation, not full reward), consume the shield from `active_powerups`, and add a `shield_used: True` field to `QuizAnswerResponse`. Frontend should show "Shield saved you!" message.
- **Effort**: S
- **Decision**: Shield grants a second chance by treating the wrong answer as correct with reduced reward. Consume after use.

### 3.5 Session Break Summary

- **Issue**: The break suggestion (`BreakSuggestion.jsx`) is a generic "Take a break!" message. The spec promises "You discovered 2 new cards and learned 3 facts."
- **Impact**: The anti-addiction messaging is the entire brand. A generic break message undermines the positioning and fails Apple's wellness app review criteria.
- **Fix**: Track per-session stats in `useGameStore.js`: `sessionNewCards`, `sessionFactsLearned`, `sessionShardsEarned`, `sessionQuizCorrect`. Pass these to `BreakSuggestion.jsx`. Display: "Nice session! You played {n} stages, discovered {n} new cards, learned {n} facts, and earned {n} shards. See you later?" Add a "Keep going" and "I'm done" button. "I'm done" navigates to the Profile page.
- **Effort**: S
- **Decision**: Implement the session summary break screen with concrete stats. This is the single most important differentiator for press and App Store featuring.

---

## 4. GAME DESIGN DECISIONS

### 4.1 Monetization Strategy

SastaHero is free with zero monetization at launch. No ads, no IAP, no premium tier.

Rationale: the anti-doom-scroll positioning is incompatible with attention-extracting monetization. The moment you add ads, the brand promise is dead. The game exists as a portfolio piece and brand builder for SastaSpace. If the game reaches 50K+ DAU, introduce a single IAP: "Supporter Pack" ($2.99) that adds a gold border to the player's profile in the community pool, 3 cosmetic card back designs, and early access to new content drops. Nothing that affects gameplay. Nothing that costs real money touches the core loop. Shards, powerups, cards, quiz content, and knowledge bank are permanently free.

### 4.2 First-Time User Experience (FTUE)

**Exact flow**:
1. App opens -> 500ms black screen with "SASTAHERO" title fade-in
2. 4-card tutorial stage (mandatory, non-skippable on first visit): cards teach UP/DOWN/LEFT/RIGHT with overlaid instruction text and a pulsing arrow indicating the correct swipe direction
3. After tutorial: "Your first real stage. 10 cards, then a quiz." (2-second overlay, auto-dismisses)
4. First real stage loads via `GET /stage`
5. After first stage completion, `StageComplete` screen shows stats
6. First quiz plays normally
7. After first quiz, show a one-time "Your Knowledge Bank is born" toast pointing to the Learn tab

**Number of tutorial stages**: 1 (the 4-card guided tutorial). The full game is unlocked immediately after.

**Gated vs open**: Nothing is gated. All tabs (Play, Cards, Story, Learn, Me) are accessible from the first second. The tutorial only intercepts the Play flow.

**Skip option**: No skip on first ever session. On subsequent visits, the tutorial never appears again (controlled by `localStorage` flag).

### 4.3 Session Design & Anti-Addiction

**Max recommended session length**: 5 minutes (~3 stages + quizzes). This is a suggestion, not an enforcement.

**Break trigger**: After every 3 stages within a single browser session.

**Break UI**: Full-screen overlay with session summary stats (new cards, facts learned, shards earned, quiz accuracy). Two buttons: "I'm done -- show me my stats" (navigates to Profile) and "One more round" (dismisses and continues). If the player hits the 6-stage mark (second break), the message shifts to "You've been here a while. Your knowledge bank grew by {n} facts today. That's worth celebrating. Come back tomorrow?"

**Daily session cap**: No hard cap. Hard caps create negative sentiment ("the game won't let me play"). Instead, diminishing returns: after 10 stages in a calendar day, shard yields drop by 50% and a persistent banner reads "Shard wells are refilling -- full rewards tomorrow." This leverages loss aversion without blocking play.

**This is a CORE DIFFERENTIATOR**: Every press pitch, every App Store screenshot, every social post leads with the anti-addiction angle. "The game that wants you to stop playing" is irresistible marketing copy.

### 4.4 Retention Mechanics

**Daily login reward**: No daily login reward. Login rewards are a dark pattern that creates obligation, not enjoyment. Instead, the streak system provides escalating value for consecutive days.

**Streak system tuning**: Current implementation: Day 3 = rare card, Day 7 = epic card, Day 14 = guaranteed legendary in next 5 stages. This is correct and stays. Add: Day 1 = 2 bonus shards (each type), Day 5 = exclusive "Devoted" badge, Day 21 = exclusive card back cosmetic, Day 30 = "Sage" title on profile. Streak reset is gentle: missing a day resets to zero with the message "Streaks reset, but your collection doesn't. Welcome back." No penalty, no shame.

**Weekly goals**: Add 3 rotating weekly goals: (1) "Discover 3 new card identities" (2) "Answer 5 quiz questions correctly" (3) "Share 10 cards to the community pool". Completing all 3 awards 10 bonus shards (2 each type). Weekly goals reset every Monday 00:00 UTC.

**Notification strategy**: Zero push notifications at launch. Push notifications for a wellness-positioned game are brand-toxic. If ever added, limit to one type: "Your weekly goals reset. New challenges await." -- maximum once per week, opt-in only.

**Lapsed player re-engagement**: When a player returns after 3+ days of inactivity, show a "Welcome back" screen with: what changed while they were gone (new community pool trends, their story chapter count), and a "catch-up bonus" of 5 shards (1 each type). This uses the curiosity gap to re-engage without guilt-tripping.

### 4.5 Economy Rebalancing

**Current shard earn rate per stage** (from code analysis):
- Full synthesize (all 10 cards swiped down): ~12-18 shards depending on rarity mix (60% common x1 + 25% uncommon x2 + 10% rare x3 + 4% epic x5 + 1% legendary x10 = expected ~1.65 per card x 10 = ~16.5 shards)
- Realistic mixed play (5 synthesize, 3 play, 1 save, 1 share): ~8-10 shards
- Quiz: 1-3 bonus shards
- Per stage total (realistic): ~10-12 shards

**Current powerup costs**: Reroll=3, Peek=2, Magnetize=5, Fusion Boost=5(1 each), Quiz Shield=4, Lucky Draw=9(3x3).

**Is the economy balanced?** Mostly, with two issues:
1. Peek (cost 2) is too cheap relative to its information value. A player spending 2 shards to see 3 upcoming cards has a massive strategic advantage. Raise to 4.
2. Lucky Draw (cost 9 of 3 different types) is too expensive for what it does (one rare+ card). This powerup will never be purchased because earning 9 shards of 3 different types requires ~3-4 stages of pure synthesis, which already yields plenty of rare cards naturally. Reduce to 2 of 3 different types (total 6).

**Rebalanced numbers**:
- Peek: 4 of any single type (was 2)
- Lucky Draw: 2 of 3 different types = 6 total (was 3 of 3 = 9)
- All others unchanged

**Time-to-first-powerup target**: 2 stages (~4 minutes). A new player synthesizing ~50% of cards earns ~5-6 shards per stage. After 2 stages: ~10-12 shards, enough for a Reroll (3) or the original Peek (2, now 4). This pacing is correct -- first powerup should feel like a reward for understanding the system, not a grind.

**Time-to-complete-collection target**: 80-120 stages (~6-10 hours of play over 2-4 weeks). With 31 identities and a natural discovery rate of ~2-3 new identities per stage initially (declining as collection fills), players should discover 80% within 30 stages and spend the remaining 50-90 stages hunting the last epic/legendary cards. This creates the "just one more stage" pull from completion bias.

### 4.6 Content Expansion Roadmap

**Current card variant count**: ~127 entries in `CARD_VARIANTS` (covers all 31 identities with 3-5 variants each).

**Target for launch**: 200 card variants. Add 73 new variants prioritizing: (1) story fragments for rare/epic/legendary cards (currently sparse), (2) knowledge facts for all categories, (3) ensuring every identity has at least 2 story, 2 knowledge, and 1 resource variant.

**Current quiz question count**: 30.

**Target for launch**: 150 quiz questions. Distribution: science (30), history (25), psychology (20), geography (20), language (15), technology (20), space (10), music (10).

**New categories**: Space, music, and technology added to quiz and knowledge systems.

**Seasonal content drops**: Monthly "knowledge packs" of 30 quiz questions + 20 card variants on a theme. First drop (Month 1): "Ocean & Marine Biology". Second drop (Month 2): "Space Exploration". Third drop (Month 3): "World Music & Instruments". This provides returning players with fresh content and creates social media moments ("New SastaHero pack dropped").

### 4.7 Social Features

**Ships at launch**: Community pool sharing (swipe left), community count visible on cards, cards_shared counter on profile. This is sufficient for launch -- the pool mechanic creates indirect social interaction without requiring friend systems.

**Ships month 1**: "Trending cards" view -- a read-only page showing the 10 most-shared card identities in the community pool with their share counts. This creates a sense of living community without exposing individual players.

**Leaderboard**: No. Leaderboards create toxic comparison and are antithetical to the wellness positioning. Instead, a "Community Stats" page showing aggregate anonymized data: total cards shared globally, total quiz questions answered correctly, total knowledge facts saved. This creates communal pride without individual ranking.

**Friend system**: Deferred to Month 3+. Scope: add friends by share code, see their collection completion %, send them a "gift shard" once per day. No chat, no messaging, no harassment surface.

**Community pool improvements**: Implement the viral credit system from the spec: when a card identity you shared gets played by 10+ other players, you receive a notification (in-app only) and a bonus rare card. This closes the generosity loop and incentivizes sharing.

### 4.8 Sound & Haptics Polish

The Web Audio synthesizer (`soundEngine.js`) is genuinely impressive for a zero-dependency implementation. 13 distinct SFX covering all game actions. Haptic patterns for swipe, combo, and milestone. The sound design is a hidden strength.

**Specific additions needed**:
1. Add a subtle ambient drone (low-pass filtered noise at 0.02 gain) that plays while cards are displayed -- creates atmosphere without being intrusive. Different pitch per card type.
2. Add a "discovery" chime for when `new_discovery` is returned from a swipe -- currently a new card collection has no audio distinction from a regular swipe.
3. Add a quiz countdown tick that accelerates in the last 3 seconds (currently `playQuizUrgent` plays the same tone repeatedly).
4. The volume control needs a slider UI, not just a mute toggle. Add to `SoundToggle.jsx`: tap to mute, long-press or swipe to adjust volume.

### 4.9 Visual Identity & Branding

**CSS-only approach: KEEP.** This is a strength, not a limitation. Zero image assets means instant load times, infinite scalability, and a distinctive brutalist identity that separates SastaHero from every glossy card game on the market. The mesh gradient cards are beautiful. The rarity glow system works. Do not add artwork.

**Color palette assessment**: The five type colors (gold/Creation, blue/Protection, red/Destruction, white-yellow/Energy, purple/Power) are well-chosen and have strong visual contrast against the black background. The one issue: ENERGY cards use yellow text on a near-white gradient (`fefce8` background in `index.css`). This fails WCAG AA contrast. Fix: darken the ENERGY gradient base to `#a16207` (amber-700) and keep text as `text-yellow-800`. This maintains the bright energy feel while meeting contrast requirements.

**App icon concept**: A black square with a single white geometric starburst (the Singularity card symbol -- the convergence of all 5 types). Minimal, brutal, unmistakable at any size. No text in the icon.

**Loading screen**: Black background, "SASTAHERO" in the brutalist font, a single animated line that expands from center to edges over 800ms. No spinner, no progress bar -- the brutalist brand extends to the loading state.

**Marketing screenshots (5 screens that sell the game)**:
1. A LEGENDARY card (Singularity) with full mesh gradient glow and "1% DROP RATE" overlay text
2. The quiz card with timer at 3 seconds (red, pulsing) and correct answer highlighted green
3. The Knowledge Bank page with 20+ saved facts, showing "Your brain after 1 week of SastaHero"
4. The StageComplete screen showing "3 new cards discovered, 5 facts learned" with the break suggestion
5. The Collection Book at 23/31 discovered with rarity glow on the epic and legendary cards

---

## 5. TECHNICAL DEBT & ARCHITECTURE

**Code quality issues**:
1. `services.py` is 1030 lines -- a God module. Split into: `stage_service.py`, `swipe_service.py`, `quiz_service.py`, `collection_service.py`, `powerup_service.py`, `story_service.py`, `knowledge_service.py`, `pool_service.py`. Each under 150 lines.
2. The `/powerup` endpoint accepts a raw `dict[str, Any]` instead of a Pydantic model (`PowerupRequest` exists in schemas but is not used in the router). Fix: use `PowerupRequest` as the request body type.
3. The `/reroll` endpoint also uses raw dict. Fix: create `RerollRequest` schema.
4. `StoryResponse.current_fragments` is typed as `list[str]` in the schema but the actual data stored is `list[dict[str, Any]]` (fragments with theme/arc metadata). This will cause serialization errors. Fix: create a `StoryFragment` schema and use `list[StoryFragment | str]`.

**Performance bottlenecks**:
1. `generate_stage` iterates the entire `card_pool` collection on every stage request (`async for entry in db.card_pool.find(...)`). At 10K DAU generating ~30 stages/day each = 300K reads/day from card_pool. Fix: cache pool counts in Redis or in-memory with a 5-minute TTL.
2. No database indexes. Add compound indexes on: `players.player_id` (unique), `player_decks.player_id + stage_number`, `card_pool.identity_id` (unique), `knowledge_bank.player_id + category`, `story_threads.player_id` (unique), `quiz_state.player_id` (unique).

**Scalability**: With MongoDB and the current architecture, 10K DAU is achievable with indexes. 100K DAU requires: Redis caching for pool counts and player shard balances, read replicas for collection/profile/knowledge queries, and rate limiting on write-heavy endpoints (swipe, quiz/answer). The stateless API design with device-ID auth scales horizontally without session affinity.

**Security audit**:
1. Player ID spoofing: any client can pass any `player_id` string. There is no authentication. This is acceptable for MVP (device-ID model), but add rate limiting: max 100 API calls per player_id per minute. Without this, a script can generate infinite shards by hammering the swipe endpoint.
2. Quiz answer validation: the correct answer index is stored server-side in `quiz_state`, which is good. But the question index (`q_idx`) is a direct index into `QUIZ_QUESTIONS` -- a malicious client can brute-force all 30 answers in seconds. Low priority since there is no competitive element.
3. No HTTPS enforcement for the Traefik proxy in local dev. Production deployment must enforce TLS.

**Database indexing** (create in a migration script):
```javascript
db.players.createIndex({ "player_id": 1 }, { unique: true })
db.player_decks.createIndex({ "player_id": 1, "stage_number": -1 })
db.player_decks.createIndex({ "player_id": 1, "cards.card_id": 1 })
db.card_pool.createIndex({ "identity_id": 1 }, { unique: true })
db.card_pool.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
db.knowledge_bank.createIndex({ "player_id": 1, "category": 1 })
db.story_threads.createIndex({ "player_id": 1 }, { unique: true })
db.quiz_state.createIndex({ "player_id": 1 }, { unique: true })
```

**Caching strategy**: Add an in-memory TTL cache (or use Traefik's built-in response cache) for: `/collection` (5-minute TTL per player), `/profile` (5-minute TTL), `/knowledge` (5-minute TTL). These are read-heavy and rarely change mid-session.

---

## 6. LAUNCH CHECKLIST

- [ ] 1. Merge feature branch to main (squash merge, run `make ci-fast`)
  - Owner: DevOps
  - Effort: S
  - Depends on: none
  - Acceptance: `make ci-fast` passes on main, card game loads at `/sastahero/`

- [ ] 2. Fix quiz shield powerup (`services.py:733-735`)
  - Owner: Backend
  - Effort: S
  - Depends on: 1
  - Acceptance: test that wrong answer with shield active returns correct=True, shield consumed

- [ ] 3. Fix Peek powerup frontend (add preview UI)
  - Owner: Frontend
  - Effort: M
  - Depends on: 1
  - Acceptance: purchasing Peek shows next 3 cards in a slide-up panel before continuing

- [ ] 4. Implement FTUE tutorial overlay
  - Owner: Frontend
  - Effort: M
  - Depends on: 1
  - Acceptance: first-time user sees 4 interactive tutorial cards, flag persists in localStorage

- [ ] 5. Expand quiz content to 150 questions
  - Owner: Design (content)
  - Effort: L
  - Depends on: 1
  - Acceptance: `len(QUIZ_QUESTIONS) >= 150`, 6+ categories, all questions have correct answer index

- [ ] 6. Expand card variants to 200 entries with 100+ knowledge facts
  - Owner: Design (content)
  - Effort: L
  - Depends on: 1
  - Acceptance: `len(CARD_VARIANTS) >= 200`, every identity has 2+ knowledge variants

- [ ] 7. Implement session summary in break suggestion
  - Owner: Frontend
  - Effort: S
  - Depends on: 1
  - Acceptance: break screen shows cards discovered, facts learned, shards earned, quiz accuracy

- [ ] 8. Add MongoDB index creation script
  - Owner: Backend/DevOps
  - Effort: S
  - Depends on: 1
  - Acceptance: script creates all 8 indexes, idempotent

- [ ] 9. Add rate limiting (100 req/min per player_id)
  - Owner: Backend
  - Effort: M
  - Depends on: 1
  - Acceptance: 101st request in 60s returns 429

- [ ] 10. Fix ENERGY card color contrast (WCAG AA)
  - Owner: Frontend
  - Effort: S
  - Depends on: 1
  - Acceptance: ENERGY gradient base darkened, text passes 4.5:1 contrast ratio

- [ ] 11. Add offline retry logic for pending swipes
  - Owner: Frontend
  - Effort: M
  - Depends on: 1
  - Acceptance: failed swipes retry on reconnect, drain queue, no duplicates

- [ ] 12. Rebalance Peek (cost 2->4) and Lucky Draw (cost 9->6)
  - Owner: Backend
  - Effort: S
  - Depends on: 1
  - Acceptance: constants updated, powerup tests pass with new costs

- [ ] 13. Split services.py into domain modules
  - Owner: Backend
  - Effort: M
  - Depends on: 2, 4
  - Acceptance: no file over 200 lines, all tests pass, imports updated

- [ ] 14. Add weekly goals system (backend + frontend)
  - Owner: Backend + Frontend
  - Effort: L
  - Depends on: 1
  - Acceptance: 3 rotating goals, progress tracking, reset Monday 00:00 UTC

- [ ] 15. Final QA pass + Playwright E2E on merged main
  - Owner: QA
  - Effort: M
  - Depends on: all above
  - Acceptance: all 26 E2E tests pass, manual play-through of 5 full sessions

---

## 7. POST-LAUNCH ROADMAP (90 Days)

### Week 1-2: Stabilization
- Monitor error rates, shard economy drift, quiz repeat frequency
- Hotfix any crash bugs or data corruption issues
- Tune break suggestion frequency based on actual session length telemetry
- Add anonymized analytics: session length, stages per session, most-swiped direction, quiz accuracy
- Add "trending cards" community view (read-only)

### Week 3-4: First Content Drop ("Ocean & Marine Biology")
- 30 new quiz questions on marine science
- 20 new card variants with ocean-themed story fragments and facts
- Add 2 new knowledge categories: marine biology, oceanography
- Social media launch: "Dive into the new Ocean pack"
- Add "discovery" SFX for new card collection events

### Month 2: Feature Expansion
- Weekly goals system (if not shipped at launch)
- Lapsed player "welcome back" screen with catch-up bonus
- Diminishing shard returns after 10 daily stages
- Community pool viral credit system (rare card reward for popular shares)
- Card detail view in Collection Book (tap to see lore, all variants discovered, shard yield)
- Profile badges with visual icons (not just text strings)

### Month 3: Growth & Virality
- Share-to-social: "Export my Knowledge Bank as an image" (list of facts learned)
- Share-to-social: "My SastaHero story, Chapter 12" (shareable story page)
- Friend system via share codes (see friend collection %, send daily gift shard)
- Second content drop: "Space Exploration"
- App Store / press outreach with anti-doom-scroll angle
- Consider Supporter Pack IAP ($2.99) if DAU exceeds 50K

---

## 8. MARKETING & POSITIONING

### App Store Description

**Title**: SastaHero -- Swipe. Learn. Collect.

**Subtitle**: The card game that replaces doom scrolling

**Description**:

Stop scrolling. Start collecting.

SastaHero is a card game designed to replace your doom-scrolling habit with something real. Swipe through beautiful cards in 3-5 minute sessions. Every swipe is a decision: play it, synthesize it for resources, save it to your collection, or share it with the world.

DISCOVER 31 UNIQUE CARDS across 5 rarity tiers. Hunt for the legendary Singularity -- only 1% of players will find it on their first day.

LEARN SOMETHING REAL. Between every stage, answer a quiz question. Science, history, psychology, geography -- your Knowledge Bank fills up with facts you actually remember. After a week, scroll through everything you learned instead of forgotten TikToks.

BUILD YOUR STORY. Every card you play adds to a unique personal narrative. Your story is different from everyone else's. Chapter by chapter, swipe by swipe.

PLAY WITH THE WORLD. Share cards to the community pool and watch them spread. See how many players collected the same rare card as you.

DESIGNED TO RESPECT YOUR TIME. SastaHero suggests breaks, celebrates your progress, and never tries to keep you playing longer than you want. No ads. No paywalls. No dark patterns.

Free. Forever. Because your attention is worth more than ads.

### Tagline
"Swipe smarter. Learn something."

### 3 Target Audience Personas

**1. Priya, 22, College Student (Mumbai)**: Deleted Instagram twice but reinstalled both times. Wants to feel productive during downtime between classes. Plays on her commute. Retention driver: Knowledge Bank ("I actually learned 50 facts this month").

**2. Jake, 28, Software Developer (Austin)**: Knows his 45-minute Reddit sessions are wasted time. Wants a "snack" game that doesn't make him feel guilty. Plays before bed. Retention driver: Collection completion ("17/31 discovered, I need that Singularity").

**3. Mei, 19, Gap Year Traveler (Berlin)**: Conscious about screen time, uses Screen Time limits already. Wants a game that fits inside her self-imposed 10-minute daily phone budget. Retention driver: Streak system + story thread ("My story is 12 chapters long and totally unique").

### Press Pitch

SastaHero is a free card game that aims to replace doom-scrolling, not replicate it. Players swipe through cards in TikTok-style sessions (3-5 minutes), but instead of disposable content, every swipe builds a card collection, teaches real facts through integrated quizzes, and generates a unique personal narrative. The game actively suggests breaks and celebrates when players stop playing. It is built entirely with CSS art (no image assets), procedural Web Audio sound design, and an anti-addiction philosophy baked into every design decision. SastaHero is available now as a free web app with no accounts required -- open the URL and start swiping.

### Social Media Launch Strategy

**Platform**: Twitter/X and Instagram, with TikTok as stretch goal.

**Pre-launch (1 week before)**: Daily "card reveal" posts showing one card identity per day with its mesh gradient, starting from Common and building to Legendary Singularity on launch day. Each post includes one fact from the game's knowledge bank.

**Launch day**: "The game that wants you to stop playing" as the hero tweet/post. Link to web app. No App Store needed (it is a web app).

**Week 1**: Daily "Did you know?" posts pulling from the quiz question database. Each ends with "Learn more like this in SastaHero."

**Ongoing**: Weekly "Community Stats" posts: "This week, SastaHero players collectively answered 10,000 quiz questions correctly and saved 5,000 facts."

### Influencer Strategy

Target micro-influencers (5K-50K followers) in the "digital wellness" and "productive screen time" niches. These creators actively seek products that align with their brand. Send them a one-paragraph pitch + direct link. Do not pay for sponsored posts -- the anti-doom-scroll angle is inherently shareable and wellness creators will post organically if the product is genuine. Avoid gaming influencers -- they will compare SastaHero to gacha games and find it lacking in depth.

---

## 9. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Content exhaustion -- 150 quiz questions depleted in 2-3 weeks by daily players | HIGH | HIGH | Monthly content drops of 30+ questions. Build a content submission pipeline for user-contributed quiz questions (moderated) by Month 3. |
| Story thread reads as incoherent gibberish due to random fragment concatenation | MEDIUM | HIGH | The arc-position sorting and theme matching in `_assemble_coherent_chapter` mitigates this, but edge cases will produce odd results. Add a "story quality" review of the first 50 generated chapters and rewrite weak fragments. Embrace quirkiness as brand charm. |
| Community pool is empty at launch (no other players to share with) | HIGH | MEDIUM | Seed the pool with 10 pre-shared card identities at varying share counts (3-50). These decay naturally via TTL if no real players interact. |
| Players do not understand 4-direction swipe mechanic | MEDIUM | HIGH | FTUE tutorial is the mitigation. Additionally, add persistent small arrow icons in the 4 corners of the card display during the first 5 stages (fade out after that). |
| WebAudio blocked by browser autoplay policies | LOW | MEDIUM | Already mitigated: `prime()` function runs on first user interaction. Silent buffer unlock pattern is industry standard. |
| MongoDB performance degrades with 100K+ player documents | LOW | MEDIUM | Indexes (Section 5) prevent this. If needed, shard by player_id hash. |
| Apple rejects PWA for "lacking native feel" during App Store review | MEDIUM | LOW | SastaHero is a web app, not an App Store submission. If native packaging is desired later, use Capacitor. |
| Players game the shard economy via rapid automated swipes | MEDIUM | MEDIUM | Rate limiting (100 req/min) prevents this. Additionally, the shard economy has no real-money exit, so gaming it yields no external value. |
| Anti-addiction positioning attracts regulatory scrutiny | LOW | LOW | SastaHero genuinely implements anti-addiction measures (break suggestions, diminishing returns, session summaries). This is a strength under regulatory review, not a weakness. |
| Feature branch merge conflicts after main has diverged | LOW | LOW | Main only added docs since the branch point (c9a56b4). Merge conflicts will be limited to Makefile and docs/. Trivially resolvable. |

---

## 10. FINAL VERDICT

**Overall game quality score**: 6.5/10

The architecture and game design are genuinely strong. The 31-card identity system with combinatorial rarity tiers is elegant. The shard economy is well-tuned. The Web Audio sound engine is a hidden gem. The CSS-only visual approach is a bold, correct call that gives SastaHero a unique identity. The backend test coverage at 90+ tests is exceptional for this stage. The anti-doom-scroll positioning is the best market angle I have seen for a casual game in 2026.

**Biggest strength**: The anti-addiction design philosophy is not bolted on -- it is the product. Break suggestions with session stats, the knowledge bank as tangible takeaway, zero monetization. This is the kind of coherent vision that gets Apple featuring and press coverage.

**Biggest weakness**: Content volume. 30 quiz questions and ~31 unique knowledge facts make the "learn something real" promise ring hollow within 3 sessions. The game's entire value proposition collapses without 5x the content. This is the single biggest gap between vision and execution.

**The ONE thing that would 10x success**: A community-contributed quiz question pipeline. If players can submit quiz questions (moderated before inclusion), the content problem solves itself exponentially. Every player becomes a content creator. The knowledge bank becomes a living, growing repository. "SastaHero now has 10,000 quiz questions -- all contributed by players" is a press headline that writes itself. Build this in Month 2.

**Recommended launch date**: 4 weeks from today (April 16, 2026). This allows time for: feature branch merge (Week 1), FTUE + critical fixes + content expansion to 150 questions (Week 2-3), QA + polish (Week 4). Delay beyond this and momentum dies.

**Confidence level**: MEDIUM. The game design is sound and the technical implementation is 62% complete. The gap is entirely in content volume and the unmarged feature branch. Both are solvable with focused effort. The risk is that content authoring takes longer than estimated -- 120 new quiz questions is 3-4 days of focused writing. If the team ships the FTUE, fixes the quiz shield, expands content to 150 questions, and merges to main, SastaHero will be a genuinely compelling product that occupies a market niche no one else is serving.
