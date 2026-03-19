"""SastaHero services — card game logic."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.sastahero.constants import (
    ALL_CARD_IDENTITIES,
    CARD_IDENTITY_MAP,
    CARD_TYPE_TO_SHARD,
    CONTENT_DISTRIBUTION,
    IDENTITIES_BY_RARITY,
    MILESTONE_THRESHOLDS,
    POOL_BASE_TTL_HOURS,
    POOL_INTERACT_EXTEND_HOURS,
    QUIZ_FAST_THRESHOLD_MS,
    RARITY_DROP_RATES,
    STAGE_SIZE,
)
from app.modules.sastahero.schemas import (
    CardInstance,
    CardType,
    CollectionEntry,
    CollectionResponse,
    ContentType,
    KnowledgeEntry,
    KnowledgeResponse,
    PlayerProfile,
    PowerupResponse,
    PowerupType,
    QuizAnswerResponse,
    QuizQuestionResponse,
    RarityTier,
    ShardBalance,
    ShardType,
    StageResponse,
    StoryChapter,
    StoryResponse,
    StreakInfo,
    SwipeResponse,
)
from app.modules.sastahero.seed.card_variants import CARD_VARIANTS
from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

# ── Variant lookup ─────────────────────────────────────────────────────

_VARIANTS_BY_IDENTITY: dict[str, list[tuple[str, str, str | None]]] = {}
for _ident_id, _ctype, _text, _cat in CARD_VARIANTS:
    _VARIANTS_BY_IDENTITY.setdefault(_ident_id, []).append((_ctype, _text, _cat))


# ── Player management ─────────────────────────────────────────────────


async def get_or_create_player(db: AsyncIOMotorDatabase[Any], player_id: str) -> dict[str, Any]:
    """Get existing player or create a new one."""
    player = await db.players.find_one({"player_id": player_id})
    if player is not None:
        return dict(player)

    now = datetime.now(tz=UTC)
    new_player: dict[str, Any] = {
        "player_id": player_id,
        "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
        "collection": [],
        "streak": {"count": 0, "last_played_date": None},
        "stages_completed": 0,
        "active_powerups": [],
        "badges": [],
        "cards_shared": 0,
        "quiz_streak": 0,
        "quiz_seen": [],
        "created_at": now,
        "updated_at": now,
    }
    await db.players.insert_one(new_player)
    return new_player


def _build_shard_balance(shards: dict[str, int]) -> ShardBalance:
    return ShardBalance(
        SOUL=shards.get("SOUL", 0),
        SHIELD=shards.get("SHIELD", 0),
        VOID=shards.get("VOID", 0),
        LIGHT=shards.get("LIGHT", 0),
        FORCE=shards.get("FORCE", 0),
    )


# ── Streak logic ──────────────────────────────────────────────────────


def _update_streak(streak: dict[str, Any]) -> dict[str, Any]:
    """Update streak based on current date vs last played date."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    last = streak.get("last_played_date")

    if last is None:
        return {"count": 1, "last_played_date": today}

    if last == today:
        return streak

    yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    if last == yesterday:
        return {"count": streak.get("count", 0) + 1, "last_played_date": today}

    # Streak broken
    return {"count": 1, "last_played_date": today}


# ── Stage generation ──────────────────────────────────────────────────


def _roll_rarity(
    boost_uncommon: bool = False,
    force_rare_plus: bool = False,
) -> RarityTier:
    """Roll a rarity tier based on drop rates, with optional boosts."""
    if force_rare_plus:
        # Only rare+ tiers
        rates = {
            RarityTier.RARE: 0.65,
            RarityTier.EPIC: 0.25,
            RarityTier.LEGENDARY: 0.10,
        }
    elif boost_uncommon:
        rates = dict(RARITY_DROP_RATES)
        rates[RarityTier.COMMON] = 0.40
        rates[RarityTier.UNCOMMON] = 0.40
    else:
        rates = dict(RARITY_DROP_RATES)

    tiers = list(rates.keys())
    weights = list(rates.values())
    return random.choices(tiers, weights=weights, k=1)[0]


def _pick_identity(rarity: RarityTier, exclude: set[str]) -> str:
    """Pick a random card identity of given rarity, avoiding duplicates."""
    candidates = [c for c in IDENTITIES_BY_RARITY.get(rarity, []) if c.id not in exclude]
    if not candidates:
        # Fallback: try any rarity that has unused identities
        for r in RarityTier:
            candidates = [c for c in IDENTITIES_BY_RARITY.get(r, []) if c.id not in exclude]
            if candidates:
                break
    if not candidates:
        # Ultimate fallback: allow duplicates from original rarity
        candidates = IDENTITIES_BY_RARITY.get(rarity, IDENTITIES_BY_RARITY[RarityTier.COMMON])
    return random.choice(candidates).id


def _pick_variant(identity_id: str, content_type: str) -> tuple[str, str | None]:
    """Pick a variant matching identity and content type. Returns (text, category)."""
    variants = _VARIANTS_BY_IDENTITY.get(identity_id, [])
    matching = [(t, c) for ct, t, c in variants if ct == content_type]
    if matching:
        return random.choice(matching)
    # Fallback to any variant
    if variants:
        ct, t, c = random.choice(variants)
        return (t, c)
    return ("A mysterious card...", None)


def _build_card_instance(
    identity_id: str, content_type: str, community_count: int = 0
) -> CardInstance:
    """Build a CardInstance from identity id and content type."""
    identity = CARD_IDENTITY_MAP[identity_id]
    text, category = _pick_variant(identity_id, content_type)
    return CardInstance(
        card_id=str(uuid.uuid4()),
        identity_id=identity_id,
        name=identity.name,
        types=identity.types,
        rarity=identity.rarity,
        shard_yield=identity.shard_yield,
        content_type=ContentType(content_type),
        text=text,
        category=category,
        community_count=community_count,
    )


async def generate_stage(db: AsyncIOMotorDatabase[Any], player_id: str) -> StageResponse:
    """Generate a new 10-card stage for the player."""
    player = await get_or_create_player(db, player_id)

    # Update streak
    new_streak = _update_streak(player["streak"])
    stages_completed = player["stages_completed"]
    stage_number = stages_completed + 1

    # Check active powerups
    powerups = player.get("active_powerups", [])
    boost_uncommon = any(p.get("type") == "FUSION_BOOST" for p in powerups)
    force_rare = any(p.get("type") == "LUCKY_DRAW" for p in powerups)
    magnetize_type = None
    for p in powerups:
        if p.get("type") == "MAGNETIZE":
            magnetize_type = p.get("shard_type")

    # Streak bonuses: inject specific cards
    streak_count = new_streak.get("count", 0)
    inject_rare = streak_count >= 3 and streak_count < 7
    inject_epic = streak_count >= 7 and streak_count < 14

    # Shuffle content types
    content_types = list(CONTENT_DISTRIBUTION)
    random.shuffle(content_types)

    # Get community pool counts
    pool_counts: dict[str, int] = {}
    async for entry in db.card_pool.find({}, {"identity_id": 1, "share_count": 1}):
        pool_counts[entry["identity_id"]] = entry.get("share_count", 0)

    # Generate cards
    cards: list[CardInstance] = []
    used_identities: set[str] = set()

    for i in range(STAGE_SIZE):
        # First card: handle force_rare from LUCKY_DRAW
        if i == 0 and force_rare:
            rarity = _roll_rarity(force_rare_plus=True)
        elif i == 0 and inject_rare:
            rarity = RarityTier.RARE
        elif i == 1 and inject_epic:
            rarity = RarityTier.EPIC
        else:
            rarity = _roll_rarity(boost_uncommon=boost_uncommon)

        # Magnetize: force type match for first 3 cards
        if magnetize_type and i < 3:
            type_enum = CardType(magnetize_type)
            typed_cards = [
                c
                for c in ALL_CARD_IDENTITIES
                if type_enum in c.types and c.id not in used_identities
            ]
            if typed_cards:
                identity_id = random.choice(typed_cards).id
            else:
                identity_id = _pick_identity(rarity, used_identities)
        else:
            identity_id = _pick_identity(rarity, used_identities)
        used_identities.add(identity_id)

        community_count = pool_counts.get(identity_id, 0)
        card = _build_card_instance(identity_id, content_types[i], community_count)
        cards.append(card)

    # Save deck
    deck_doc: dict[str, Any] = {
        "player_id": player_id,
        "stage_number": stage_number,
        "cards": [c.model_dump() for c in cards],
        "swipe_history": [],
        "completed": False,
        "created_at": datetime.now(tz=UTC),
    }
    await db.player_decks.insert_one(deck_doc)

    # Consume one-shot powerups
    remaining_powerups: list[dict[str, Any]] = []
    for p in powerups:
        if p.get("type") in ("LUCKY_DRAW", "MAGNETIZE"):
            continue  # consumed
        if p.get("type") == "FUSION_BOOST":
            stages_left = p.get("stages_left", 2) - 1
            if stages_left > 0:
                remaining_powerups.append({**p, "stages_left": stages_left})
            continue
        remaining_powerups.append(p)

    # Update player
    await db.players.update_one(
        {"player_id": player_id},
        {
            "$set": {
                "streak": new_streak,
                "active_powerups": remaining_powerups,
                "updated_at": datetime.now(tz=UTC),
            }
        },
    )

    return StageResponse(
        stage_number=stage_number,
        cards=cards,
        shards=_build_shard_balance(player["shards"]),
        stages_completed=stages_completed,
    )


# ── Swipe processing ─────────────────────────────────────────────────


async def process_swipe(
    db: AsyncIOMotorDatabase[Any],
    player_id: str,
    card_id: str,
    action: str,
) -> SwipeResponse:
    """Process a swipe action on a card."""
    player = await get_or_create_player(db, player_id)
    shards = dict(player["shards"])
    collection: list[str] = list(player.get("collection", []))
    collection_updated = False
    new_discovery: str | None = None
    shard_changes: dict[str, int] = {}

    # Find the card in any active deck
    deck = await db.player_decks.find_one(
        {
            "player_id": player_id,
            "cards.card_id": card_id,
        }
    )

    card_data: dict[str, Any] | None = None
    if deck:
        for c in deck["cards"]:
            if c["card_id"] == card_id:
                card_data = c
                break

    if card_data is None:
        # Return current state if card not found
        return SwipeResponse(shards=_build_shard_balance(shards))

    identity_id = card_data["identity_id"]
    card_types = card_data.get("types", [])
    shard_yield = card_data.get("shard_yield", 1)

    if action == "UP":
        # Play: add to story thread, mark in collection
        if identity_id not in collection:
            collection.append(identity_id)
            collection_updated = True
            new_discovery = identity_id

        # Append to story fragments
        text = card_data.get("text", "")
        if text:
            story = await db.story_threads.find_one({"player_id": player_id})
            if story is None:
                await db.story_threads.insert_one(
                    {
                        "player_id": player_id,
                        "chapters": [],
                        "current_fragments": [text],
                    }
                )
            else:
                fragments = story.get("current_fragments", [])
                fragments.append(text)
                # Every 10 played cards = new chapter
                if len(fragments) >= 10:
                    chapter_text = " ".join(fragments)
                    chapters = story.get("chapters", [])
                    chapter_num = len(chapters) + 1
                    chapters.append(
                        {
                            "number": chapter_num,
                            "text": chapter_text,
                            "card_count": len(fragments),
                            "created_at": datetime.now(tz=UTC),
                        }
                    )
                    await db.story_threads.update_one(
                        {"player_id": player_id},
                        {"$set": {"chapters": chapters, "current_fragments": []}},
                    )
                else:
                    await db.story_threads.update_one(
                        {"player_id": player_id},
                        {"$set": {"current_fragments": fragments}},
                    )

    elif action == "DOWN":
        # Synthesize: award shards based on card types
        for ct_str in card_types:
            ct = CardType(ct_str)
            shard_type = CARD_TYPE_TO_SHARD[ct].value
            shards[shard_type] = shards.get(shard_type, 0) + shard_yield
            shard_changes[shard_type] = shard_changes.get(shard_type, 0) + shard_yield

    elif action == "RIGHT":
        # Save: add to collection
        if identity_id not in collection:
            collection.append(identity_id)
            collection_updated = True
            new_discovery = identity_id

        # If knowledge card, save to knowledge bank
        if card_data.get("content_type") == "KNOWLEDGE" and card_data.get("text"):
            await db.knowledge_bank.insert_one(
                {
                    "player_id": player_id,
                    "fact_id": card_id,
                    "text": card_data["text"],
                    "category": card_data.get("category", "general"),
                    "saved_at": datetime.now(tz=UTC),
                }
            )

    elif action == "LEFT":
        # Share: add to community pool, award 1 random shard
        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(hours=POOL_BASE_TTL_HOURS)
        await db.card_pool.update_one(
            {"identity_id": identity_id},
            {
                "$inc": {"share_count": 1},
                "$set": {"expires_at": expires_at, "updated_at": now},
                "$setOnInsert": {"identity_id": identity_id, "created_at": now},
            },
            upsert=True,
        )

        random_shard = random.choice(list(ShardType)).value
        shards[random_shard] = shards.get(random_shard, 0) + 1
        shard_changes[random_shard] = 1

        # Increment cards_shared
        await db.players.update_one(
            {"player_id": player_id},
            {"$inc": {"cards_shared": 1}},
        )

    # Record swipe in deck
    await db.player_decks.update_one(
        {"player_id": player_id, "cards.card_id": card_id},
        {
            "$push": {
                "swipe_history": {
                    "card_id": card_id,
                    "action": action,
                    "timestamp": datetime.now(tz=UTC),
                }
            }
        },
    )

    # Update player shards and collection
    update: dict[str, Any] = {
        "$set": {
            "shards": shards,
            "collection": collection,
            "updated_at": datetime.now(tz=UTC),
        }
    }
    await db.players.update_one({"player_id": player_id}, update)

    return SwipeResponse(
        shards=_build_shard_balance(shards),
        collection_updated=collection_updated,
        new_discovery=new_discovery,
        shard_changes=shard_changes,
    )


# ── Stage completion ──────────────────────────────────────────────────


async def complete_stage(
    db: AsyncIOMotorDatabase[Any], player_id: str, stage_number: int
) -> dict[str, Any]:
    """Mark a stage as completed and check for milestones."""
    await db.player_decks.update_one(
        {"player_id": player_id, "stage_number": stage_number},
        {"$set": {"completed": True}},
    )

    result = await db.players.find_one_and_update(
        {"player_id": player_id},
        {"$inc": {"stages_completed": 1}},
        return_document=True,
    )

    stages_completed = result["stages_completed"] if result else 0
    milestone_reward: dict[str, Any] | None = None

    if stages_completed in MILESTONE_THRESHOLDS:
        milestone_reward = _get_milestone_reward(stages_completed)
        if milestone_reward and result:
            # Apply shard rewards
            if "shards" in milestone_reward:
                shard_updates = {}
                for shard_type, amount in milestone_reward["shards"].items():
                    shard_updates[f"shards.{shard_type}"] = amount
                if shard_updates:
                    await db.players.update_one(
                        {"player_id": player_id},
                        {"$inc": shard_updates},
                    )
            # Apply badge
            if "badge" in milestone_reward:
                await db.players.update_one(
                    {"player_id": player_id},
                    {"$addToSet": {"badges": milestone_reward["badge"]}},
                )

    return {
        "stages_completed": stages_completed,
        "milestone": milestone_reward,
    }


def _get_milestone_reward(stages: int) -> dict[str, Any] | None:
    """Get the reward for reaching a milestone."""
    rewards: dict[int, dict[str, Any]] = {
        5: {
            "shards": {s.value: 1 for s in ShardType},
            "message": "5 stages! 5 random shards earned.",
        },
        10: {"message": "10 stages! A rare card awaits next stage."},
        25: {"badge": "explorer_25", "message": "25 stages! Explorer badge earned."},
        50: {"message": "50 stages! Legendary card guaranteed next stage."},
        100: {
            "badge": "master_100",
            "shards": {s.value: 10 for s in ShardType},
            "message": "100 stages! Master title + 50 bonus shards!",
        },
    }
    return rewards.get(stages)


# ── Quiz ──────────────────────────────────────────────────────────────


async def get_quiz_question(db: AsyncIOMotorDatabase[Any], player_id: str) -> QuizQuestionResponse:
    """Get a quiz question the player hasn't seen recently."""
    player = await get_or_create_player(db, player_id)
    seen = set(player.get("quiz_seen", []))

    # Find unseen questions
    available = [(i, q) for i, q in enumerate(QUIZ_QUESTIONS) if str(i) not in seen]
    if not available:
        # Reset seen list
        await db.players.update_one(
            {"player_id": player_id},
            {"$set": {"quiz_seen": []}},
        )
        available = list(enumerate(QUIZ_QUESTIONS))

    idx, (question, options, correct_idx, category, difficulty) = random.choice(available)
    question_id = str(idx)

    # Store correct answer in DB for validation
    await db.quiz_state.update_one(
        {"player_id": player_id},
        {
            "$set": {
                "current_question_id": question_id,
                "correct_index": correct_idx,
            }
        },
        upsert=True,
    )

    return QuizQuestionResponse(
        question_id=question_id,
        question=question,
        options=options,
        time_limit=15,
    )


async def submit_quiz_answer(
    db: AsyncIOMotorDatabase[Any],
    player_id: str,
    question_id: str,
    selected_index: int,
    time_taken_ms: int,
) -> QuizAnswerResponse:
    """Process a quiz answer and return rewards."""
    player = await get_or_create_player(db, player_id)

    # Get correct answer
    q_idx = int(question_id)
    if q_idx < 0 or q_idx >= len(QUIZ_QUESTIONS):
        return QuizAnswerResponse(correct=False, correct_index=0)

    _, _, correct_idx, _, _ = QUIZ_QUESTIONS[q_idx]

    # Fix 1: Timeout guard — negative index means no answer was selected
    if selected_index < 0:
        # Mark question as seen but award nothing
        await db.players.update_one(
            {"player_id": player_id},
            {"$set": {"quiz_streak": 0}, "$addToSet": {"quiz_seen": question_id}},
        )
        return QuizAnswerResponse(
            correct=False,
            correct_index=correct_idx,
            reward_shards=0,
            streak_count=0,
            bonus_card=False,
        )

    correct = selected_index == correct_idx

    quiz_streak = player.get("quiz_streak", 0)
    reward_shards = 0
    bonus_card = False

    # Check quiz shield powerup
    powerups = player.get("active_powerups", [])
    has_shield = any(p.get("type") == "QUIZ_SHIELD" for p in powerups)

    if correct:
        if time_taken_ms < QUIZ_FAST_THRESHOLD_MS:
            reward_shards = 3
            bonus_card = True  # guaranteed uncommon next stage
        else:
            reward_shards = 2
        quiz_streak += 1

        if quiz_streak >= 3:
            bonus_card = True  # rare card next stage
    elif has_shield:
        # Fix 2: Quiz Shield — wrong answer but shield active
        # Don't break streak, award 50% of normal correct reward (1 shard)
        reward_shards = 1
        # quiz_streak preserved (not reset)
        # Consume the shield
        powerups = [p for p in powerups if p.get("type") != "QUIZ_SHIELD"]
    else:
        reward_shards = 1
        quiz_streak = 0

    # Award shards (random type)
    shard_updates: dict[str, int] = {}
    for _ in range(reward_shards):
        shard_type = random.choice(list(ShardType)).value
        shard_updates[f"shards.{shard_type}"] = shard_updates.get(f"shards.{shard_type}", 0) + 1

    update: dict[str, Any] = {
        "$set": {
            "quiz_streak": quiz_streak,
            "active_powerups": powerups,
        },
        "$addToSet": {"quiz_seen": question_id},
    }
    if shard_updates:
        update["$inc"] = shard_updates

    await db.players.update_one({"player_id": player_id}, update)

    return QuizAnswerResponse(
        correct=correct,
        correct_index=correct_idx,
        reward_shards=reward_shards,
        streak_count=quiz_streak,
        bonus_card=bonus_card,
    )


# ── Collection ────────────────────────────────────────────────────────


async def get_collection(db: AsyncIOMotorDatabase[Any], player_id: str) -> CollectionResponse:
    """Get the player's collection book."""
    player = await get_or_create_player(db, player_id)
    discovered = set(player.get("collection", []))

    entries = [
        CollectionEntry(
            identity_id=card.id,
            name=card.name,
            types=card.types,
            rarity=card.rarity,
            discovered=card.id in discovered,
        )
        for card in ALL_CARD_IDENTITIES
    ]

    return CollectionResponse(
        entries=entries,
        discovered=len(discovered),
        total=len(ALL_CARD_IDENTITIES),
    )


# ── Shards ────────────────────────────────────────────────────────────


async def get_shards(db: AsyncIOMotorDatabase[Any], player_id: str) -> ShardBalance:
    """Get the player's shard balances."""
    player = await get_or_create_player(db, player_id)
    return _build_shard_balance(player["shards"])


# ── Profile ───────────────────────────────────────────────────────────


async def get_profile(db: AsyncIOMotorDatabase[Any], player_id: str) -> PlayerProfile:
    """Get the player's profile."""
    player = await get_or_create_player(db, player_id)
    collection = player.get("collection", [])

    return PlayerProfile(
        player_id=player_id,
        stages_completed=player.get("stages_completed", 0),
        streak=StreakInfo(
            count=player["streak"].get("count", 0),
            last_played_date=player["streak"].get("last_played_date"),
        ),
        badges=player.get("badges", []),
        community_score=player.get("cards_shared", 0),
        cards_shared=player.get("cards_shared", 0),
        collection_pct=round(len(collection) / len(ALL_CARD_IDENTITIES) * 100, 1)
        if ALL_CARD_IDENTITIES
        else 0.0,
    )


# ── Powerups ──────────────────────────────────────────────────────────


def _deduct_any_single(shards: dict[str, int], cost: int) -> bool:
    """Deduct `cost` from the first shard type that has enough. Returns success."""
    for st in ShardType:
        if shards.get(st.value, 0) >= cost:
            shards[st.value] -= cost
            return True
    return False


def _deduct_magnetize(shards: dict[str, int], shard_type: str | None) -> tuple[bool, str | None]:
    """Deduct 5 shards for MAGNETIZE; auto-picks highest type if none given."""
    if not shard_type:
        best = max(ShardType, key=lambda st: shards.get(st.value, 0))
        if shards.get(best.value, 0) >= 5:
            shard_type = best.value
    if shard_type and shards.get(shard_type, 0) >= 5:
        shards[shard_type] -= 5
        return True, shard_type
    return False, shard_type


def _deduct_fusion_boost(shards: dict[str, int]) -> bool:
    """Deduct 1 of each shard type for FUSION_BOOST."""
    if all(shards.get(st.value, 0) >= 1 for st in ShardType):
        for st in ShardType:
            shards[st.value] -= 1
        return True
    return False


def _deduct_lucky_draw(shards: dict[str, int]) -> bool:
    """Deduct 3 each from 3 different shard types for LUCKY_DRAW."""
    affordable = [st for st in ShardType if shards.get(st.value, 0) >= 3]
    if len(affordable) >= 3:
        for st in affordable[:3]:
            shards[st.value] -= 3
        return True
    return False


def _generate_peek_preview() -> list[CardInstance]:
    """Generate a 3-card preview for the PEEK powerup."""
    cards: list[CardInstance] = []
    used: set[str] = set()
    content_types = ["STORY", "KNOWLEDGE", "RESOURCE"]
    for i in range(3):
        rarity = _roll_rarity()
        identity_id = _pick_identity(rarity, used)
        used.add(identity_id)
        cards.append(_build_card_instance(identity_id, content_types[i]))
    return cards


async def purchase_powerup(
    db: AsyncIOMotorDatabase[Any],
    player_id: str,
    powerup_type: str,
    shard_type: str | None = None,
) -> PowerupResponse:
    """Purchase a powerup, deducting shards."""
    player = await get_or_create_player(db, player_id)
    shards = dict(player["shards"])
    powerups = list(player.get("active_powerups", []))

    pt = PowerupType(powerup_type)
    success = False

    if pt == PowerupType.REROLL:
        success = _deduct_any_single(shards, 3)
    elif pt == PowerupType.PEEK:
        success = _deduct_any_single(shards, 2)
    elif pt == PowerupType.MAGNETIZE:
        success, shard_type = _deduct_magnetize(shards, shard_type)
    elif pt == PowerupType.FUSION_BOOST:
        success = _deduct_fusion_boost(shards)
    elif pt == PowerupType.QUIZ_SHIELD:
        success = _deduct_any_single(shards, 4)
    elif pt == PowerupType.LUCKY_DRAW:
        success = _deduct_lucky_draw(shards)

    peek_preview: list[CardInstance] | None = None

    if success:
        powerup_entry: dict[str, Any] = {"type": powerup_type}
        if pt == PowerupType.MAGNETIZE and shard_type:
            powerup_entry["shard_type"] = shard_type
        if pt == PowerupType.FUSION_BOOST:
            powerup_entry["stages_left"] = 2
        powerups.append(powerup_entry)

        if pt == PowerupType.PEEK:
            peek_preview = _generate_peek_preview()

        await db.players.update_one(
            {"player_id": player_id},
            {
                "$set": {
                    "shards": shards,
                    "active_powerups": powerups,
                    "updated_at": datetime.now(tz=UTC),
                }
            },
        )

    return PowerupResponse(
        success=success,
        shards=_build_shard_balance(shards),
        active_powerups=[p.get("type", "") for p in powerups],
        peek_preview=peek_preview,
    )


# ── Story ─────────────────────────────────────────────────────────────


async def get_story(db: AsyncIOMotorDatabase[Any], player_id: str) -> StoryResponse:
    """Get the player's story thread."""
    story = await db.story_threads.find_one({"player_id": player_id})
    if story is None:
        return StoryResponse(chapters=[], current_fragments=[], total_chapters=0)

    chapters = [
        StoryChapter(
            number=ch["number"],
            text=ch["text"],
            card_count=ch.get("card_count", 0),
            created_at=ch.get("created_at", datetime.now(tz=UTC)),
        )
        for ch in story.get("chapters", [])
    ]

    return StoryResponse(
        chapters=chapters,
        current_fragments=story.get("current_fragments", []),
        total_chapters=len(chapters),
    )


# ── Knowledge ─────────────────────────────────────────────────────────


async def get_knowledge(
    db: AsyncIOMotorDatabase[Any], player_id: str, category: str | None = None
) -> KnowledgeResponse:
    """Get the player's knowledge bank."""
    query: dict[str, Any] = {"player_id": player_id}
    if category:
        query["category"] = category

    facts: list[KnowledgeEntry] = []
    async for entry in db.knowledge_bank.find(query).sort("saved_at", -1):
        facts.append(
            KnowledgeEntry(
                text=entry["text"],
                category=entry.get("category", "general"),
                saved_at=entry.get("saved_at", datetime.now(tz=UTC)),
            )
        )

    # Get distinct categories
    all_categories: list[str] = await db.knowledge_bank.distinct(
        "category", {"player_id": player_id}
    )

    return KnowledgeResponse(
        facts=facts,
        categories=sorted(all_categories),
        total=len(facts),
    )


# ── Reroll (powerup) ─────────────────────────────────────────────────


async def reroll_card(
    db: AsyncIOMotorDatabase[Any], player_id: str, card_id: str
) -> CardInstance | None:
    """Replace a card in the current deck (Reroll powerup)."""
    player = await get_or_create_player(db, player_id)
    powerups = player.get("active_powerups", [])

    has_reroll = any(p.get("type") == "REROLL" for p in powerups)
    if not has_reroll:
        return None

    # Find the deck with this card
    deck = await db.player_decks.find_one(
        {
            "player_id": player_id,
            "cards.card_id": card_id,
            "completed": False,
        }
    )
    if not deck:
        return None

    # Get used identities in this deck
    used = {c["identity_id"] for c in deck["cards"]}

    # Generate replacement
    rarity = _roll_rarity()
    identity_id = _pick_identity(rarity, used)
    new_card = _build_card_instance(identity_id, "STORY")

    # Replace in deck
    cards = deck["cards"]
    for i, c in enumerate(cards):
        if c["card_id"] == card_id:
            cards[i] = new_card.model_dump()
            break

    await db.player_decks.update_one(
        {"_id": deck["_id"]},
        {"$set": {"cards": cards}},
    )

    # Remove reroll from powerups
    new_powerups = [p for p in powerups if p.get("type") != "REROLL"]
    await db.players.update_one(
        {"player_id": player_id},
        {"$set": {"active_powerups": new_powerups}},
    )

    return new_card


# ── Community pool extend TTL ─────────────────────────────────────────


async def extend_pool_ttl(db: AsyncIOMotorDatabase[Any], identity_id: str) -> None:
    """Extend a community pool entry's TTL when someone interacts with it."""
    now = datetime.now(tz=UTC)
    new_expiry = now + timedelta(hours=POOL_INTERACT_EXTEND_HOURS)
    await db.card_pool.update_one(
        {"identity_id": identity_id},
        {"$set": {"expires_at": new_expiry}},
    )
