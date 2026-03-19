# SastaHero Game Design Spec

## Overview

SastaHero is an endless-scrolling card game designed to counter doom scrolling. Players swipe through cards in a vertical feed (like TikTok), but instead of mindless consumption, each swipe is a meaningful decision that builds their collection, shapes a personal story, and teaches them something new.

**Target audience:** 16-30 year olds who lose 30-60 min daily to TikTok/Instagram doom scrolling.
**Session length:** 3-5 minutes (2-3 stages + quizzes).
**Platform:** Mobile-first web app (React), works on desktop too.

## Core Game Loop

### The Feed

Player sees one card at a time, full screen. Each card has art, a type badge, rarity indicator, and content (story fragment, fact, or resource).

### Stage = 10 Cards

Backend generates a deck of 10 cards per stage based on:
- Player's current collection (avoids duplicates unless rare)
- Community pool influence (shared cards appear more often)
- Weighted randomness by card type
- Combo cards sprinkled in based on rarity tier

### Four Swipe Actions

| Swipe | Action | Effect |
|-------|--------|--------|
| **Up** | Play | Card enters active board, contributes to story/progression, consumed |
| **Down** | Synthesize | Card breaks into shards of its type (yield scales with rarity) |
| **Right** | Save | Card goes into personal collection/inventory |
| **Left** | Share | Card enters community pool, drop rate increases globally, player earns 1 random shard |

### Between Stages

A knowledge/quiz card appears. Correct answer = bonus shards or guaranteed uncommon+ card. Wrong answer = see the correct answer, learn something, move on. No punishment.

### Every 5 Stages = Milestone

Collection progress snapshot, streak counter, total shards earned. Small celebration moment.

## Card System & Rarity

### Five Card Types

Inspired by five primordial forces (with subtle roots in Indian cosmology — Brahma, Vishnu, Shiva, Surya, Shakti — but presented universally with no mythological narrative).

| Type | Color Identity | Vibe |
|------|---------------|------|
| **Creation** | Gold/Amber | Building, birth, new beginnings |
| **Protection** | Blue/Silver | Defense, preservation, stability |
| **Destruction** | Red/Dark | Breaking, change, clearing the old |
| **Energy** | White/Yellow | Light, fuel, momentum |
| **Power** | Purple/Deep | Force, authority, amplification |

### Rarity Tiers (Based on Combinations)

| Tier | Combo | Count | Drop Rate | Shard Yield |
|------|-------|-------|-----------|-------------|
| **Common** | Single type | 5 | ~60% | 1 shard |
| **Uncommon** | 2-type combo | 10 | ~25% | 2 shards |
| **Rare** | 3-type combo | 10 | ~10% | 3 shards |
| **Epic** | 4-type combo | 5 | ~4% | 5 shards |
| **Legendary** | All 5 types | 1 | ~1% | 10 shards |

31 total unique card identities. Each identity has multiple content variants so encountering the same combo type still feels fresh.

### Card Content Types (Mixed Per Stage)

- **Story cards** (~5 per stage) — narrative snippets, character moments, world-building fragments
- **Knowledge cards** (~3 per stage) — fun facts, "did you know", bite-sized information
- **Resource cards** (~2 per stage) — pure shard value, no content payload, quick synthesize fodder

### Example Combo Cards

- Creation + Destruction (Uncommon) = "Rebirth" — something ends so something new begins
- Protection + Energy (Uncommon) = "Barrier" — charged defense
- Creation + Protection + Power (Rare) = "Fortress" — building something unbreakable
- All 5 (Legendary) = "Singularity" — the ultimate convergence

## Resource Economy

### Five Shard Types

| Shard | Source |
|-------|--------|
| **Soul Shards** | Synthesizing Creation cards |
| **Shield Shards** | Synthesizing Protection cards |
| **Void Shards** | Synthesizing Destruction cards |
| **Light Shards** | Synthesizing Energy cards |
| **Force Shards** | Synthesizing Power cards |

Combo cards yield shards of all their component types (e.g. synthesizing a Creation+Destruction uncommon gives 1 Soul Shard + 1 Void Shard).

### Powerups

| Powerup | Cost | Effect |
|---------|------|--------|
| **Reroll** | 3 of any single type | Swap current card for a new random one |
| **Peek** | 2 of any single type | Preview the next 3 cards in stage |
| **Magnetize** | 5 of one type | Next stage has 3+ guaranteed cards of that type |
| **Fusion Boost** | 1 of each type (5 total) | Double combo card drop rate for 2 stages |
| **Quiz Shield** | 4 of any single type | Second chance on next quiz question |
| **Lucky Draw** | 3 of 3 different types | Force one Rare+ card into next stage |

### Economy Balance

- Average stage yields ~12-15 shards if everything is synthesized (but then nothing is saved/played — that's the tension)
- Most powerups cost 1-2 stages worth of shards
- No real-money purchases. No ads. Anti-doom-scroll, not a new addiction vector.

## Community Sharing (Swipe Left)

### Pool Mechanics

- Every shared card gets a share count — how many players have shared that card identity
- Higher share count = higher probability of appearing in other players' stages
- Cards nobody shares gradually fade from the pool (natural curation)
- Pool is per-card-identity, not per-content-variant

### Rewards for Sharing

- 1 random shard immediately
- Sharer's credit: if your shared card gets played (swiped up) by 10+ other players, earn a bonus rare card
- Visible "shared by you" counter on profile — contribution score

### Design Principles

- Content scaling: more players = richer card pool for everyone
- Generosity loop: sharing is an investment, not a sacrifice
- No toxicity: players share cards, not messages. No chat, no comments, no harassment surface

### What Players See

- Small counter on each card: "47 players have this" (common) vs "2 players have this" (feels special)
- Profile shows: total cards shared, community impact score, how many players benefited

## Knowledge & Quiz System

### Knowledge Cards In-Stage (~3 per stage)

- Bite-sized facts: science, history, psychology, geography, language
- Same swipe mechanics — save (right) interesting facts to personal Knowledge Bank
- Categories rotate per stage

### Quiz Between Stages

- One question after every stage (10 cards then quiz then next 10)
- Multiple choice, 4 options, 15 second timer
- Topics sourced from facts the player has seen recently (reinforces retention)
- Difficulty scales gently over time

### Quiz Rewards

| Result | Reward |
|--------|--------|
| Correct (fast, <5s) | 3 bonus shards + guaranteed uncommon next stage |
| Correct (normal) | 2 bonus shards |
| Wrong | See correct answer, 1 consolation shard |
| Streak bonus (3 correct in a row) | 1 rare card added to next stage |

### Knowledge Bank

- Every knowledge card swiped right gets saved here
- Browsable by category
- A personal "things I've learned" journal — the anti-doom-scroll payoff
- After a week of playing, scroll through actual retained facts instead of forgotten TikToks

### Content Sourcing (MVP)

- Curated database of ~500 facts + ~200 quiz questions
- Categorized and tagged by topic
- Backend serves them, avoiding repeats per player

## Player Progression & Retention

No levels, no XP bars. Progression is organic and multi-dimensional.

### Collection Book

- 31 card identities to discover
- Each identity has a page that fills in on first encounter
- Completion percentage is primary progression metric: "You've discovered 19/31 cards"
- Completing a rarity tier unlocks a cosmetic badge

### Streaks

- Daily streak counter
- Streak rewards: Day 3 = rare card, Day 7 = epic card, Day 14 = guaranteed legendary in next 5 stages
- Missing a day resets to zero — gently, no shaming

### Story Threads

- Cards swiped up (played) accumulate into a personal story thread
- Every 10 played cards = a "chapter" auto-generated from narrative fragments
- Players read back their unique story — different for everyone
- Long-term hook: "my story is 47 chapters long and totally unique"

### Milestone Rewards

| Milestone | Reward |
|-----------|--------|
| 5 stages | 5 random shards |
| 10 stages | 1 guaranteed rare card |
| 25 stages | Profile badge + 1 epic card |
| 50 stages | Legendary card guaranteed next stage |
| 100 stages | Unique profile title + all-shard bonus |

### Session Design

- 3-5 minutes per session (2-3 stages + quizzes)
- Game suggests breaks: "Nice session! You discovered 2 new cards and learned 3 facts. See you later?"
- No infinite loop pressure — actively encourages healthy stopping points

## Technical Architecture

### Stack

Fits into existing SastaSpace: React 18 + Vite (frontend), FastAPI + MongoDB (backend), Traefik (routing), Docker Compose (orchestration).

### Database Collections (MongoDB)

| Collection | Purpose |
|------------|---------|
| `cards` | Master card definitions — type, rarity, combo, content variants |
| `card_pool` | Community pool — card identity, share count, decay timestamp |
| `players` | Player profile — collection, shards, streaks, stats |
| `player_decks` | Active stage state — current 10 cards, swipe history |
| `story_threads` | Played cards accumulated into chapters |
| `knowledge_bank` | Facts/quizzes saved per player |
| `quiz_questions` | Curated quiz content — question, options, answer, category |
| `facts` | Curated fact database — content, category, tags |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sastahero/stage` | GET | Generate next 10-card stage for player |
| `/api/v1/sastahero/swipe` | POST | Process swipe action (up/down/left/right) |
| `/api/v1/sastahero/quiz` | GET | Get quiz question between stages |
| `/api/v1/sastahero/quiz/answer` | POST | Submit quiz answer, return result + reward |
| `/api/v1/sastahero/collection` | GET | Player's collection book state |
| `/api/v1/sastahero/shards` | GET | Current shard balances |
| `/api/v1/sastahero/powerup` | POST | Spend shards on a powerup |
| `/api/v1/sastahero/story` | GET | Player's story thread / chapters |
| `/api/v1/sastahero/knowledge` | GET | Player's saved knowledge bank |
| `/api/v1/sastahero/profile` | GET | Stats, streaks, badges, community score |

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `CardFeed` | Full-screen vertical card display, swipe detection |
| `CardDisplay` | Single card rendering — art, type badge, content, rarity glow |
| `SwipeHandler` | Touch/mouse gesture detection for 4-direction swipes |
| `QuizCard` | Between-stage quiz UI — question, 4 options, timer |
| `ShardBar` | Persistent top bar showing 5 shard counts |
| `PowerupPanel` | Slide-up panel to spend shards on powerups |
| `CollectionBook` | Grid view of all 31 card identities, fill state |
| `StoryThread` | Scrollable chapter view of played cards |
| `KnowledgeBank` | Browsable saved facts by category |
| `ProfilePage` | Stats, streaks, badges, community score |
| `MilestonePopup` | Celebration overlay every 5 stages |

### Swipe Detection

Touch events on mobile, mouse drag on desktop. Threshold + direction detection (custom or `react-swipeable`).

### State Flow

1. Player opens game -> `GET /stage` -> receive 10 cards
2. Player swipes each card -> `POST /swipe` -> backend processes action, returns updated shards/collection
3. After 10 swipes -> `GET /quiz` -> show quiz
4. Answer quiz -> `POST /quiz/answer` -> get rewards
5. Loop back to step 1

## Existing Code

The current SastaHero codebase is an RPG character builder (class selector, stat allocator, hero card export). This will be **fully replaced** with the card game. The existing backend module (`backend/app/modules/sastahero/`) and frontend (`frontends/sastahero/`) will be rewritten. The Docker/Traefik/routing infrastructure remains unchanged.

## Authentication Model

**Approach: Anonymous / Device-ID Sessions (zero friction)**

Time-to-first-swipe must be as fast as opening TikTok. No login screen.

- Generate a UUID on the client, store in localStorage, use as `player_id` in MongoDB
- All player state (collection, shards, streaks, story) keyed to this device ID
- Future: "Link Account / Save Progress" in settings menu to tie to a permanent SastaSpace identity
- If localStorage is cleared, player starts fresh (acceptable for MVP)

## Community Pool Decay

**Approach: TTL Index + Activity Multiplier**

Prevents `card_pool` from growing infinitely with abandoned cards.

- Every shared card gets a baseline expiration of **48 hours**
- Every time another player interacts with that card (plays, saves, or shares it), push expiration out by **12 hours**
- MongoDB TTL index on the `expires_at` field handles automatic cleanup
- Popular/viral cards stay alive indefinitely through organic interaction
- Dead cards self-prune without any cron jobs

## Story Chapter Generation

**Approach: Structured Concatenation (Mad-Libs Style) for MVP**

No AI narrative engine — story card text is designed as modular sentence fragments.

- Card content is authored to work as appendable fragments (e.g., "The earth split open," + "revealing a glowing artifact," + "which pulsed with chaotic energy.")
- When a player swipes up, the fragment appends to their story thread
- Every 10 played cards = one chapter (just the concatenated text with a chapter number)
- Occasional clunkiness adds quirky charm — this is a feature, not a bug
- AI-powered narrative smoothing deferred to future phase

## Card Art & Visuals

**Approach: CSS-Driven Abstract Art / Typography**

No commissioned artwork. The brutalist design system carries the visuals.

- Dark, minimalist card UI with intense color identity (Gold, Blue, Red, White, Purple)
- Animated CSS mesh gradients per card type — each type has a distinct visual feel
- Glowing borders for rarity tiers (subtle for common, intense for legendary)
- Crisp typography for card content — the text IS the art
- Keeps React bundle size negligible, no image assets to load
- Card type icons (simple SVG glyphs) for quick visual identification

## Optimistic UI

**Critical for the swipe-to-swipe flow feeling instant.**

Every `POST /swipe` cannot block the next card. The game must feel as fluid as TikTok scrolling.

- Swipe registered locally in Zustand store immediately
- Shard counts, collection state, and story thread update on the client optimistically
- Network request fires in background (`POST /swipe`)
- If the request fails, queue for retry (up to 3 attempts) — do not roll back UI state for transient errors
- Batch swipe events if player is swiping faster than network can resolve (send accumulated swipes in one request at stage end as fallback)
- Stage-end sync: `GET /stage` for next stage also returns authoritative shard/collection state, correcting any drift

## Content Model (MVP)

- **Hand-craft ~100 seed cards** across all 5 types and rarity tiers — polished, balanced, set the tone
- **Story card text authored as modular fragments** — designed to concatenate into readable narrative chunks
- **~500 curated facts** across categories (science, history, psychology, geography, language)
- **~200 quiz questions** with 4 options each, tagged by category and difficulty
- **Community sharing grows the pool organically** — more players = more content
- **AI generation deferred** to future phase
