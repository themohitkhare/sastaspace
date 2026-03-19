"""SastaHero Pydantic schemas — card game models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ──────────────────────────────────────────────────────────────


class CardType(str, Enum):
    CREATION = "CREATION"
    PROTECTION = "PROTECTION"
    DESTRUCTION = "DESTRUCTION"
    ENERGY = "ENERGY"
    POWER = "POWER"


class RarityTier(str, Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ContentType(str, Enum):
    STORY = "STORY"
    KNOWLEDGE = "KNOWLEDGE"
    RESOURCE = "RESOURCE"


class SwipeAction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class ShardType(str, Enum):
    SOUL = "SOUL"
    SHIELD = "SHIELD"
    VOID = "VOID"
    LIGHT = "LIGHT"
    FORCE = "FORCE"


class PowerupType(str, Enum):
    REROLL = "REROLL"
    PEEK = "PEEK"
    MAGNETIZE = "MAGNETIZE"
    FUSION_BOOST = "FUSION_BOOST"
    QUIZ_SHIELD = "QUIZ_SHIELD"
    LUCKY_DRAW = "LUCKY_DRAW"


# ── Card Schemas ───────────────────────────────────────────────────────


class CardIdentity(BaseModel):
    id: str
    name: str
    types: list[CardType]
    rarity: RarityTier
    shard_yield: int


class CardVariant(BaseModel):
    identity_id: str
    content_type: ContentType
    text: str
    category: str | None = None


class CardInstance(BaseModel):
    card_id: str
    identity_id: str
    name: str
    types: list[CardType]
    rarity: RarityTier
    shard_yield: int
    content_type: ContentType
    text: str
    category: str | None = None
    community_count: int = 0


# ── Player Schemas ─────────────────────────────────────────────────────


class ShardBalance(BaseModel):
    SOUL: int = 0
    SHIELD: int = 0
    VOID: int = 0
    LIGHT: int = 0
    FORCE: int = 0


class StreakInfo(BaseModel):
    count: int = 0
    last_played_date: str | None = None


class PlayerProfile(BaseModel):
    player_id: str
    stages_completed: int = 0
    streak: StreakInfo = Field(default_factory=StreakInfo)
    badges: list[str] = Field(default_factory=list)
    community_score: int = 0
    cards_shared: int = 0
    collection_pct: float = 0.0


# ── Stage / Swipe Schemas ─────────────────────────────────────────────


class StageResponse(BaseModel):
    stage_number: int
    cards: list[CardInstance]
    shards: ShardBalance
    stages_completed: int


class SwipeRequest(BaseModel):
    player_id: str
    card_id: str
    action: SwipeAction


class SwipeResponse(BaseModel):
    shards: ShardBalance
    collection_updated: bool = False
    new_discovery: str | None = None
    shard_changes: dict[str, int] = Field(default_factory=dict)


# ── Quiz Schemas ───────────────────────────────────────────────────────


class QuizQuestionResponse(BaseModel):
    question_id: str
    question: str
    options: list[str]
    time_limit: int = 15


class QuizAnswerRequest(BaseModel):
    player_id: str
    question_id: str
    selected_index: int
    time_taken_ms: int


class QuizAnswerResponse(BaseModel):
    correct: bool
    correct_index: int
    reward_shards: int = 0
    streak_count: int = 0
    bonus_card: bool = False


# ── Powerup Schemas ────────────────────────────────────────────────────


class PowerupRequest(BaseModel):
    player_id: str
    powerup_type: PowerupType
    shard_type: ShardType | None = None  # required for MAGNETIZE


class PowerupResponse(BaseModel):
    success: bool
    shards: ShardBalance
    active_powerups: list[str]
    peek_preview: list[CardInstance] | None = None


# ── Collection Schemas ─────────────────────────────────────────────────


class CollectionEntry(BaseModel):
    identity_id: str
    name: str
    types: list[CardType]
    rarity: RarityTier
    discovered: bool = False


class CollectionResponse(BaseModel):
    entries: list[CollectionEntry]
    discovered: int
    total: int


# ── Story Schemas ──────────────────────────────────────────────────────


class StoryChapter(BaseModel):
    number: int
    text: str
    card_count: int
    created_at: datetime


class StoryResponse(BaseModel):
    chapters: list[StoryChapter]
    current_fragments: list[str]
    total_chapters: int


# ── Knowledge Schemas ──────────────────────────────────────────────────


class KnowledgeEntry(BaseModel):
    text: str
    category: str
    saved_at: datetime


class KnowledgeResponse(BaseModel):
    facts: list[KnowledgeEntry]
    categories: list[str]
    total: int
