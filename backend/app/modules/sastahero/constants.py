"""SastaHero constants — card definitions, drop rates, shard costs."""

from app.modules.sastahero.schemas import (
    CardIdentity,
    CardType,
    PowerupType,
    RarityTier,
    ShardType,
)

# ── Type-to-Shard mapping ─────────────────────────────────────────────

CARD_TYPE_TO_SHARD: dict[CardType, ShardType] = {
    CardType.CREATION: ShardType.SOUL,
    CardType.PROTECTION: ShardType.SHIELD,
    CardType.DESTRUCTION: ShardType.VOID,
    CardType.ENERGY: ShardType.LIGHT,
    CardType.POWER: ShardType.FORCE,
}

# ── Drop rates ─────────────────────────────────────────────────────────

RARITY_DROP_RATES: dict[RarityTier, float] = {
    RarityTier.COMMON: 0.60,
    RarityTier.UNCOMMON: 0.25,
    RarityTier.RARE: 0.10,
    RarityTier.EPIC: 0.04,
    RarityTier.LEGENDARY: 0.01,
}

RARITY_SHARD_YIELD: dict[RarityTier, int] = {
    RarityTier.COMMON: 1,
    RarityTier.UNCOMMON: 2,
    RarityTier.RARE: 3,
    RarityTier.EPIC: 5,
    RarityTier.LEGENDARY: 10,
}

# ── Content type distribution per stage ────────────────────────────────

STAGE_SIZE = 10
CONTENT_DISTRIBUTION: list[str] = ["STORY"] * 5 + ["KNOWLEDGE"] * 3 + ["RESOURCE"] * 2

# ── Powerup costs ──────────────────────────────────────────────────────
# Costs are expressed as {shard_type: amount} or special keys:
# "any_single": N means N of any one shard type
# "each": N means N of every shard type
# "any_three_different": N means N each of 3 different types

POWERUP_COSTS: dict[PowerupType, dict[str, int]] = {
    PowerupType.REROLL: {"any_single": 3},
    PowerupType.PEEK: {"any_single": 2},
    PowerupType.MAGNETIZE: {"specific": 5},
    PowerupType.FUSION_BOOST: {"each": 1},
    PowerupType.QUIZ_SHIELD: {"any_single": 4},
    PowerupType.LUCKY_DRAW: {"any_three_different": 3},
}

# ── Milestone rewards ─────────────────────────────────────────────────

MILESTONE_THRESHOLDS: list[int] = [5, 10, 25, 50, 100]

# ── Community pool TTL (seconds) ──────────────────────────────────────

POOL_BASE_TTL_HOURS = 48
POOL_INTERACT_EXTEND_HOURS = 12

# ── Quiz rewards ──────────────────────────────────────────────────────

QUIZ_FAST_THRESHOLD_MS = 5000
QUIZ_TIME_LIMIT = 15

# ── All 31 card identities ────────────────────────────────────────────

C = CardType.CREATION
P = CardType.PROTECTION
D = CardType.DESTRUCTION
E = CardType.ENERGY
Pw = CardType.POWER

ALL_CARD_IDENTITIES: list[CardIdentity] = [
    # 5 Common (single type)
    CardIdentity(id="genesis", name="Genesis", types=[C], rarity=RarityTier.COMMON, shard_yield=1),
    CardIdentity(id="aegis", name="Aegis", types=[P], rarity=RarityTier.COMMON, shard_yield=1),
    CardIdentity(id="entropy", name="Entropy", types=[D], rarity=RarityTier.COMMON, shard_yield=1),
    CardIdentity(id="spark", name="Spark", types=[E], rarity=RarityTier.COMMON, shard_yield=1),
    CardIdentity(
        id="dominion", name="Dominion", types=[Pw], rarity=RarityTier.COMMON, shard_yield=1
    ),
    # 10 Uncommon (2-type combos)
    CardIdentity(
        id="guardian", name="Guardian", types=[C, P], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(
        id="rebirth", name="Rebirth", types=[C, D], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(id="dawn", name="Dawn", types=[C, E], rarity=RarityTier.UNCOMMON, shard_yield=2),
    CardIdentity(
        id="architect", name="Architect", types=[C, Pw], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(
        id="barrier", name="Barrier", types=[P, D], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(
        id="radiance", name="Radiance", types=[P, E], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(
        id="sentinel", name="Sentinel", types=[P, Pw], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(
        id="wildfire", name="Wildfire", types=[D, E], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    CardIdentity(id="ruin", name="Ruin", types=[D, Pw], rarity=RarityTier.UNCOMMON, shard_yield=2),
    CardIdentity(
        id="surge", name="Surge", types=[E, Pw], rarity=RarityTier.UNCOMMON, shard_yield=2
    ),
    # 10 Rare (3-type combos)
    CardIdentity(
        id="fortress",
        name="Fortress",
        types=[C, P, D],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="aurora",
        name="Aurora",
        types=[C, P, E],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="throne",
        name="Throne",
        types=[C, P, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="phoenix",
        name="Phoenix",
        types=[C, D, E],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="cataclysm",
        name="Cataclysm",
        types=[C, D, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="nova",
        name="Nova",
        types=[C, E, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="bastion",
        name="Bastion",
        types=[P, D, E],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="warden",
        name="Warden",
        types=[P, D, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="beacon",
        name="Beacon",
        types=[P, E, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    CardIdentity(
        id="tempest",
        name="Tempest",
        types=[D, E, Pw],
        rarity=RarityTier.RARE,
        shard_yield=3,
    ),
    # 5 Epic (4-type combos)
    CardIdentity(
        id="eclipse",
        name="Eclipse",
        types=[C, P, D, E],
        rarity=RarityTier.EPIC,
        shard_yield=5,
    ),
    CardIdentity(
        id="oblivion",
        name="Oblivion",
        types=[C, P, D, Pw],
        rarity=RarityTier.EPIC,
        shard_yield=5,
    ),
    CardIdentity(
        id="ascension",
        name="Ascension",
        types=[C, P, E, Pw],
        rarity=RarityTier.EPIC,
        shard_yield=5,
    ),
    CardIdentity(
        id="maelstrom",
        name="Maelstrom",
        types=[C, D, E, Pw],
        rarity=RarityTier.EPIC,
        shard_yield=5,
    ),
    CardIdentity(
        id="nexus",
        name="Nexus",
        types=[P, D, E, Pw],
        rarity=RarityTier.EPIC,
        shard_yield=5,
    ),
    # 1 Legendary (all 5 types)
    CardIdentity(
        id="singularity",
        name="Singularity",
        types=[C, P, D, E, Pw],
        rarity=RarityTier.LEGENDARY,
        shard_yield=10,
    ),
]

# Quick lookup by id
CARD_IDENTITY_MAP: dict[str, CardIdentity] = {c.id: c for c in ALL_CARD_IDENTITIES}

# Group by rarity
IDENTITIES_BY_RARITY: dict[RarityTier, list[CardIdentity]] = {}
for _card in ALL_CARD_IDENTITIES:
    IDENTITIES_BY_RARITY.setdefault(_card.rarity, []).append(_card)
