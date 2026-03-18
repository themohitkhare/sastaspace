"""Tests for SastaHero card game API endpoints."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock MongoDB database."""
    db = AsyncMock()
    # Default returns
    db.players.find_one = AsyncMock(return_value=None)
    db.players.insert_one = AsyncMock()
    db.players.update_one = AsyncMock()
    db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 1})
    db.player_decks.insert_one = AsyncMock()
    db.player_decks.update_one = AsyncMock()
    db.player_decks.find_one = AsyncMock(return_value=None)
    db.story_threads.find_one = AsyncMock(return_value=None)
    db.story_threads.insert_one = AsyncMock()
    db.story_threads.update_one = AsyncMock()
    db.knowledge_bank.insert_one = AsyncMock()
    db.card_pool.update_one = AsyncMock()
    db.quiz_state.update_one = AsyncMock()

    # card_pool.find returns async iterator
    def _empty_pool_find(*_args: Any, **_kwargs: Any) -> "_AsyncCursorMock":
        return _AsyncCursorMock([])

    db.card_pool.find = _empty_pool_find

    return db


class _AsyncCursorMock:
    """Mock for MongoDB async cursor."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> "_AsyncCursorMock":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def _override_db(mock_db: AsyncMock) -> None:
    """Override the get_db dependency."""
    from app.db.session import get_db

    async def _mock_get_db():  # type: ignore[no-untyped-def]
        yield mock_db

    app.dependency_overrides[get_db] = _mock_get_db


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ── Schema Tests ───────────────────────────────────────────────────────


class TestSchemas:
    def test_card_types_exist(self) -> None:
        from app.modules.sastahero.schemas import CardType

        assert len(CardType) == 5
        assert CardType.CREATION.value == "CREATION"

    def test_rarity_tiers_exist(self) -> None:
        from app.modules.sastahero.schemas import RarityTier

        assert len(RarityTier) == 5
        assert RarityTier.LEGENDARY.value == "LEGENDARY"

    def test_shard_balance_defaults(self) -> None:
        from app.modules.sastahero.schemas import ShardBalance

        balance = ShardBalance()
        assert balance.SOUL == 0
        assert balance.SHIELD == 0

    def test_card_instance_model(self) -> None:
        from app.modules.sastahero.schemas import CardInstance, CardType, ContentType, RarityTier

        card = CardInstance(
            card_id="test-id",
            identity_id="genesis",
            name="Genesis",
            types=[CardType.CREATION],
            rarity=RarityTier.COMMON,
            shard_yield=1,
            content_type=ContentType.STORY,
            text="Test text",
        )
        assert card.card_id == "test-id"
        assert card.community_count == 0

    def test_swipe_actions(self) -> None:
        from app.modules.sastahero.schemas import SwipeAction

        assert SwipeAction.UP.value == "UP"
        assert SwipeAction.DOWN.value == "DOWN"
        assert SwipeAction.LEFT.value == "LEFT"
        assert SwipeAction.RIGHT.value == "RIGHT"

    def test_powerup_types(self) -> None:
        from app.modules.sastahero.schemas import PowerupType

        assert len(PowerupType) == 6


# ── Constants Tests ────────────────────────────────────────────────────


class TestConstants:
    def test_all_31_card_identities(self) -> None:
        from app.modules.sastahero.constants import ALL_CARD_IDENTITIES

        assert len(ALL_CARD_IDENTITIES) == 31

    def test_identity_rarity_distribution(self) -> None:
        from app.modules.sastahero.constants import IDENTITIES_BY_RARITY, RarityTier

        assert len(IDENTITIES_BY_RARITY[RarityTier.COMMON]) == 5
        assert len(IDENTITIES_BY_RARITY[RarityTier.UNCOMMON]) == 10
        assert len(IDENTITIES_BY_RARITY[RarityTier.RARE]) == 10
        assert len(IDENTITIES_BY_RARITY[RarityTier.EPIC]) == 5
        assert len(IDENTITIES_BY_RARITY[RarityTier.LEGENDARY]) == 1

    def test_identity_map_lookup(self) -> None:
        from app.modules.sastahero.constants import CARD_IDENTITY_MAP

        assert "genesis" in CARD_IDENTITY_MAP
        assert "singularity" in CARD_IDENTITY_MAP
        assert CARD_IDENTITY_MAP["singularity"].name == "Singularity"

    def test_drop_rates_sum_to_one(self) -> None:
        from app.modules.sastahero.constants import RARITY_DROP_RATES

        total = sum(RARITY_DROP_RATES.values())
        assert abs(total - 1.0) < 0.01

    def test_card_type_to_shard_mapping(self) -> None:
        from app.modules.sastahero.constants import CARD_TYPE_TO_SHARD, CardType, ShardType

        assert CARD_TYPE_TO_SHARD[CardType.CREATION] == ShardType.SOUL
        assert CARD_TYPE_TO_SHARD[CardType.DESTRUCTION] == ShardType.VOID


# ── Seed Data Tests ────────────────────────────────────────────────────


class TestSeedData:
    def test_card_variants_reference_valid_identities(self) -> None:
        from app.modules.sastahero.constants import CARD_IDENTITY_MAP
        from app.modules.sastahero.seed.card_variants import CARD_VARIANTS

        for ident_id, _, _, _ in CARD_VARIANTS:
            assert ident_id in CARD_IDENTITY_MAP, f"Unknown identity: {ident_id}"

    def test_all_identities_have_variants(self) -> None:
        from app.modules.sastahero.constants import ALL_CARD_IDENTITIES
        from app.modules.sastahero.seed.card_variants import CARD_VARIANTS

        variant_identities = {v[0] for v in CARD_VARIANTS}
        for card in ALL_CARD_IDENTITIES:
            assert card.id in variant_identities, f"No variants for: {card.id}"

    def test_quiz_questions_have_valid_structure(self) -> None:
        from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

        assert len(QUIZ_QUESTIONS) >= 20
        for q, opts, correct_idx, cat, diff in QUIZ_QUESTIONS:
            assert len(opts) == 4
            assert 0 <= correct_idx < 4
            assert isinstance(cat, str)
            assert isinstance(diff, int)

    def test_card_variants_content_types_valid(self) -> None:
        from app.modules.sastahero.seed.card_variants import CARD_VARIANTS

        valid_types = {"STORY", "KNOWLEDGE", "RESOURCE"}
        for _, content_type, _, _ in CARD_VARIANTS:
            assert content_type in valid_types


# ── Stage Generation Tests ─────────────────────────────────────────────


class TestStageGeneration:
    def test_stage_returns_10_cards(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player-1")
            assert response.status_code == 200
            data = response.json()
            assert len(data["cards"]) == 10
            assert "stage_number" in data
            assert "shards" in data
        finally:
            _clear_overrides()

    def test_stage_cards_have_required_fields(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player-2")
            data = response.json()
            for card in data["cards"]:
                assert "card_id" in card
                assert "identity_id" in card
                assert "name" in card
                assert "types" in card
                assert "rarity" in card
                assert "shard_yield" in card
                assert "content_type" in card
                assert "text" in card
        finally:
            _clear_overrides()

    def test_stage_no_duplicate_identities(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player-3")
            data = response.json()
            identity_ids = [c["identity_id"] for c in data["cards"]]
            assert len(identity_ids) == len(set(identity_ids))
        finally:
            _clear_overrides()

    def test_stage_creates_player_if_not_exists(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        _override_db(mock_db)
        try:
            client.get("/api/v1/sastahero/stage?player_id=new-player")
            mock_db.players.insert_one.assert_called_once()
        finally:
            _clear_overrides()

    def test_stage_requires_player_id(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/stage")
            assert response.status_code == 422
        finally:
            _clear_overrides()


# ── Swipe Processing Tests ────────────────────────────────────────────


class TestSwipeProcessing:
    def _setup_deck(self, mock_db: AsyncMock) -> str:
        """Set up a mock deck with a card."""
        card_id = "test-card-1"
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "stage_number": 1,
                "cards": [
                    {
                        "card_id": card_id,
                        "identity_id": "genesis",
                        "name": "Genesis",
                        "types": ["CREATION"],
                        "rarity": "COMMON",
                        "shard_yield": 1,
                        "content_type": "STORY",
                        "text": "From the silence, something stirred—",
                        "category": None,
                    }
                ],
            }
        )
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 5, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 1, "last_played_date": "2026-03-18"},
                "stages_completed": 1,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        return card_id

    def test_swipe_up_adds_to_collection(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        card_id = self._setup_deck(mock_db)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={
                    "player_id": "test-player",
                    "card_id": card_id,
                    "action": "UP",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["collection_updated"] is True
            assert data["new_discovery"] == "genesis"
        finally:
            _clear_overrides()

    def test_swipe_down_awards_shards(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        card_id = self._setup_deck(mock_db)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={
                    "player_id": "test-player",
                    "card_id": card_id,
                    "action": "DOWN",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["shards"]["SOUL"] == 6  # was 5, +1 for creation card
            assert data["shard_changes"]["SOUL"] == 1
        finally:
            _clear_overrides()

    def test_swipe_right_saves_to_collection(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        card_id = self._setup_deck(mock_db)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={
                    "player_id": "test-player",
                    "card_id": card_id,
                    "action": "RIGHT",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["collection_updated"] is True
        finally:
            _clear_overrides()

    def test_swipe_left_shares_to_pool(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        card_id = self._setup_deck(mock_db)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={
                    "player_id": "test-player",
                    "card_id": card_id,
                    "action": "LEFT",
                },
            )
            assert response.status_code == 200
            data = response.json()
            # Should have 1 random shard added
            total_shards = sum(data["shards"].values())
            assert total_shards == 6  # was 5 total, +1 random
            mock_db.card_pool.update_one.assert_called_once()
        finally:
            _clear_overrides()

    def test_swipe_invalid_action(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={
                    "player_id": "test-player",
                    "card_id": "test-card",
                    "action": "INVALID",
                },
            )
            assert response.status_code == 422
        finally:
            _clear_overrides()


# ── Quiz Tests ─────────────────────────────────────────────────────────


class TestQuiz:
    def test_get_quiz_returns_question(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert "question_id" in data
            assert "question" in data
            assert len(data["options"]) == 4
            assert data["time_limit"] == 15
        finally:
            _clear_overrides()

    def test_quiz_answer_correct_fast(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            # First get a question to know the correct answer
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_data = quiz_resp.json()
            q_id = q_data["question_id"]

            # Get correct answer from seed data
            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": correct_idx,
                    "time_taken_ms": 3000,  # fast
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["correct"] is True
            assert data["reward_shards"] == 3
            assert data["bonus_card"] is True
        finally:
            _clear_overrides()

    def test_quiz_answer_correct_normal(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_data = quiz_resp.json()
            q_id = q_data["question_id"]

            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": correct_idx,
                    "time_taken_ms": 10000,  # normal speed
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["correct"] is True
            assert data["reward_shards"] == 2
        finally:
            _clear_overrides()

    def test_quiz_answer_wrong(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_data = quiz_resp.json()
            q_id = q_data["question_id"]

            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]
            wrong_idx = (correct_idx + 1) % 4

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": wrong_idx,
                    "time_taken_ms": 8000,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["correct"] is False
            assert data["reward_shards"] == 1
            assert data["correct_index"] == correct_idx
        finally:
            _clear_overrides()


# ── Collection Tests ───────────────────────────────────────────────────


class TestCollection:
    def test_collection_returns_31_entries(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/collection?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 31
            assert len(data["entries"]) == 31
        finally:
            _clear_overrides()

    def test_collection_marks_discovered(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": ["genesis", "aegis"],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            response = client.get("/api/v1/sastahero/collection?player_id=test-player")
            data = response.json()
            assert data["discovered"] == 2
            discovered_ids = [e["identity_id"] for e in data["entries"] if e["discovered"]]
            assert "genesis" in discovered_ids
            assert "aegis" in discovered_ids
        finally:
            _clear_overrides()


# ── Profile Tests ──────────────────────────────────────────────────────


class TestProfile:
    def test_profile_returns_stats(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 10, "SHIELD": 5, "VOID": 3, "LIGHT": 7, "FORCE": 2},
                "collection": ["genesis", "aegis", "entropy"],
                "streak": {"count": 3, "last_played_date": "2026-03-18"},
                "stages_completed": 15,
                "active_powerups": [],
                "badges": ["explorer_25"],
                "cards_shared": 8,
                "quiz_streak": 2,
                "quiz_seen": [],
            }
        )
        try:
            response = client.get("/api/v1/sastahero/profile?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["stages_completed"] == 15
            assert data["streak"]["count"] == 3
            assert data["cards_shared"] == 8
            assert data["collection_pct"] > 0
        finally:
            _clear_overrides()


# ── Shards Tests ───────────────────────────────────────────────────────


class TestShards:
    def test_shards_returns_balance(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 10, "SHIELD": 5, "VOID": 3, "LIGHT": 7, "FORCE": 2},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            response = client.get("/api/v1/sastahero/shards?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["SOUL"] == 10
            assert data["FORCE"] == 2
        finally:
            _clear_overrides()


# ── Powerup Tests ──────────────────────────────────────────────────────


class TestPowerups:
    def test_purchase_reroll_success(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 5, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={
                    "player_id": "test-player",
                    "powerup_type": "REROLL",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["shards"]["SOUL"] == 2  # 5 - 3
            assert "REROLL" in data["active_powerups"]
        finally:
            _clear_overrides()

    def test_purchase_insufficient_shards(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 0, "SHIELD": 0, "VOID": 0, "LIGHT": 0, "FORCE": 0},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={
                    "player_id": "test-player",
                    "powerup_type": "REROLL",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
        finally:
            _clear_overrides()

    def test_purchase_fusion_boost(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "shards": {"SOUL": 5, "SHIELD": 5, "VOID": 5, "LIGHT": 5, "FORCE": 5},
                "collection": [],
                "streak": {"count": 0, "last_played_date": None},
                "stages_completed": 0,
                "active_powerups": [],
                "badges": [],
                "cards_shared": 0,
                "quiz_streak": 0,
                "quiz_seen": [],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={
                    "player_id": "test-player",
                    "powerup_type": "FUSION_BOOST",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Each shard type reduced by 1
            assert data["shards"]["SOUL"] == 4
            assert data["shards"]["FORCE"] == 4
        finally:
            _clear_overrides()


# ── Story Tests ────────────────────────────────────────────────────────


class TestStory:
    def test_story_empty_for_new_player(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.get("/api/v1/sastahero/story?player_id=new-player")
            assert response.status_code == 200
            data = response.json()
            assert data["chapters"] == []
            assert data["current_fragments"] == []
            assert data["total_chapters"] == 0
        finally:
            _clear_overrides()

    def test_story_with_chapters(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.story_threads.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "chapters": [
                    {
                        "number": 1,
                        "text": "The story begins here.",
                        "card_count": 10,
                        "created_at": "2026-03-18T00:00:00Z",
                    }
                ],
                "current_fragments": ["A new fragment,"],
            }
        )
        try:
            response = client.get("/api/v1/sastahero/story?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["total_chapters"] == 1
            assert len(data["current_fragments"]) == 1
        finally:
            _clear_overrides()


# ── Knowledge Tests ────────────────────────────────────────────────────


class TestKnowledge:
    def test_knowledge_empty_for_new_player(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.knowledge_bank.find = lambda *_a, **_k: _SortableCursorMock([])
        mock_db.knowledge_bank.distinct = AsyncMock(return_value=[])
        try:
            response = client.get("/api/v1/sastahero/knowledge?player_id=new-player")
            assert response.status_code == 200
            data = response.json()
            assert data["facts"] == []
            assert data["total"] == 0
        finally:
            _clear_overrides()

    def test_knowledge_with_facts(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.knowledge_bank.find = lambda *_a, **_k: _SortableCursorMock(
            [
                {
                    "player_id": "test-player",
                    "text": "A cool fact",
                    "category": "science",
                    "saved_at": "2026-03-18T00:00:00Z",
                }
            ]
        )
        mock_db.knowledge_bank.distinct = AsyncMock(return_value=["science"])
        try:
            response = client.get("/api/v1/sastahero/knowledge?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["facts"][0]["category"] == "science"
            assert "science" in data["categories"]
        finally:
            _clear_overrides()


class _SortableCursorMock:
    """Mock for MongoDB cursor with sort()."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items
        self._index = 0

    def sort(self, *args: Any, **kwargs: Any) -> "_SortableCursorMock":
        return self

    def __aiter__(self) -> "_SortableCursorMock":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item
