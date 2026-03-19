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

    def sort(self, *_args: Any, **_kwargs: Any) -> "_SortableCursorMock":
        return self

    def __aiter__(self) -> "_SortableCursorMock":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


# ── Helper: standard player fixture ───────────────────────────────────


def _make_player(**overrides: Any) -> dict[str, Any]:
    """Build a standard player dict with optional overrides."""
    base: dict[str, Any] = {
        "player_id": "test-player",
        "shards": {"SOUL": 10, "SHIELD": 10, "VOID": 10, "LIGHT": 10, "FORCE": 10},
        "collection": [],
        "streak": {"count": 0, "last_played_date": None},
        "stages_completed": 0,
        "active_powerups": [],
        "badges": [],
        "cards_shared": 0,
        "quiz_streak": 0,
        "quiz_seen": [],
    }
    base.update(overrides)
    return base


def _make_deck_card(
    card_id: str = "card-1",
    identity_id: str = "genesis",
    types: list[str] | None = None,
    content_type: str = "STORY",
    text: str = "Test text",
    shard_yield: int = 1,
) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "identity_id": identity_id,
        "name": identity_id.title(),
        "types": types or ["CREATION"],
        "rarity": "COMMON",
        "shard_yield": shard_yield,
        "content_type": content_type,
        "text": text,
        "category": "science" if content_type == "KNOWLEDGE" else None,
    }


# ── Streak Unit Tests ─────────────────────────────────────────────────


class TestStreakLogic:
    def test_streak_new_player(self) -> None:
        from app.modules.sastahero.services import _update_streak

        result = _update_streak({"count": 0, "last_played_date": None})
        assert result["count"] == 1
        assert result["last_played_date"] is not None

    def test_streak_same_day(self) -> None:
        from datetime import UTC, datetime

        from app.modules.sastahero.services import _update_streak

        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        result = _update_streak({"count": 3, "last_played_date": today})
        assert result["count"] == 3  # unchanged

    def test_streak_consecutive_day(self) -> None:
        from datetime import UTC, datetime, timedelta

        from app.modules.sastahero.services import _update_streak

        yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        result = _update_streak({"count": 5, "last_played_date": yesterday})
        assert result["count"] == 6

    def test_streak_broken(self) -> None:
        from app.modules.sastahero.services import _update_streak

        result = _update_streak({"count": 10, "last_played_date": "2020-01-01"})
        assert result["count"] == 1  # reset


# ── Roll Rarity Unit Tests ────────────────────────────────────────────


class TestRollRarity:
    def test_roll_default(self) -> None:
        from app.modules.sastahero.services import _roll_rarity

        results = {_roll_rarity() for _ in range(200)}
        assert len(results) >= 2  # should hit multiple rarities

    def test_roll_force_rare_plus(self) -> None:
        from app.modules.sastahero.schemas import RarityTier
        from app.modules.sastahero.services import _roll_rarity

        for _ in range(50):
            r = _roll_rarity(force_rare_plus=True)
            assert r in (RarityTier.RARE, RarityTier.EPIC, RarityTier.LEGENDARY)

    def test_roll_boost_uncommon(self) -> None:
        from app.modules.sastahero.services import _roll_rarity

        results = [_roll_rarity(boost_uncommon=True) for _ in range(200)]
        from app.modules.sastahero.schemas import RarityTier

        uncommon_count = sum(1 for r in results if r == RarityTier.UNCOMMON)
        assert uncommon_count > 20  # should be significantly higher than default


# ── Pick Identity Fallbacks ───────────────────────────────────────────


class TestPickIdentity:
    def test_fallback_to_other_rarity(self) -> None:
        from app.modules.sastahero.constants import IDENTITIES_BY_RARITY
        from app.modules.sastahero.schemas import RarityTier
        from app.modules.sastahero.services import _pick_identity

        # Exclude all commons — should fall back to another rarity
        all_common_ids = {c.id for c in IDENTITIES_BY_RARITY[RarityTier.COMMON]}
        result = _pick_identity(RarityTier.COMMON, all_common_ids)
        assert result not in all_common_ids

    def test_ultimate_fallback(self) -> None:
        from app.modules.sastahero.constants import ALL_CARD_IDENTITIES
        from app.modules.sastahero.schemas import RarityTier
        from app.modules.sastahero.services import _pick_identity

        # Exclude ALL identities — should still return something (duplicate)
        all_ids = {c.id for c in ALL_CARD_IDENTITIES}
        result = _pick_identity(RarityTier.COMMON, all_ids)
        assert result is not None


# ── Pick Variant Fallbacks ────────────────────────────────────────────


class TestPickVariant:
    def test_matching_variant(self) -> None:
        from app.modules.sastahero.services import _pick_variant

        text, cat = _pick_variant("genesis", "STORY")
        assert text != ""
        assert text != "A mysterious card..."

    def test_fallback_to_any_variant(self) -> None:
        from app.modules.sastahero.services import _pick_variant

        text, _ = _pick_variant("genesis", "NONEXISTENT_TYPE")
        assert text != "A mysterious card..."  # should use any variant

    def test_fallback_unknown_identity(self) -> None:
        from app.modules.sastahero.services import _pick_variant

        text, cat = _pick_variant("nonexistent_card", "STORY")
        assert text == "A mysterious card..."
        assert cat is None


# ── Stage Generation with Powerups ─────────────────────────────────────


class TestStageWithPowerups:
    def test_stage_with_lucky_draw(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "LUCKY_DRAW"}])
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert len(data["cards"]) == 10
        finally:
            _clear_overrides()

    def test_stage_with_magnetize(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(
                active_powerups=[{"type": "MAGNETIZE", "shard_type": "CREATION"}]
            )
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
            cards = response.json()["cards"]
            assert len(cards) == 10
            # At least some creation-type cards in first 3
            creation_first3 = sum(1 for c in cards[:3] if "CREATION" in c["types"])
            assert creation_first3 >= 1
        finally:
            _clear_overrides()

    def test_stage_with_fusion_boost(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "FUSION_BOOST", "stages_left": 2}])
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
            assert len(response.json()["cards"]) == 10
        finally:
            _clear_overrides()

    def test_stage_with_fusion_boost_last_stage(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "FUSION_BOOST", "stages_left": 1}])
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
        finally:
            _clear_overrides()

    def test_stage_streak_injects_rare(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(streak={"count": 4, "last_played_date": "2020-01-01"})
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
        finally:
            _clear_overrides()

    def test_stage_streak_injects_epic(self, client: TestClient, mock_db: AsyncMock) -> None:
        from datetime import UTC, datetime, timedelta

        yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(streak={"count": 8, "last_played_date": yesterday})
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
        finally:
            _clear_overrides()

    def test_stage_with_community_pool(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)

        def _pool_find(*_args: Any, **_kwargs: Any) -> _AsyncCursorMock:
            return _AsyncCursorMock([{"identity_id": "genesis", "share_count": 50}])

        mock_db.card_pool.find = _pool_find
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
        finally:
            _clear_overrides()

    def test_stage_other_powerup_preserved(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "QUIZ_SHIELD"}])
        )
        try:
            response = client.get("/api/v1/sastahero/stage?player_id=test-player")
            assert response.status_code == 200
        finally:
            _clear_overrides()


# ── Swipe Edge Cases ──────────────────────────────────────────────────


class TestSwipeEdgeCases:
    def test_swipe_card_not_found(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        mock_db.player_decks.find_one = AsyncMock(return_value=None)
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "missing", "action": "UP"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["collection_updated"] is False
        finally:
            _clear_overrides()

    def test_swipe_up_existing_story(self, client: TestClient, mock_db: AsyncMock) -> None:
        """UP swipe appends to existing story fragments."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "cards": [_make_deck_card()],
            }
        )
        mock_db.story_threads.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "chapters": [],
                "current_fragments": ["frag1", "frag2"],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "card-1", "action": "UP"},
            )
            assert response.status_code == 200
            mock_db.story_threads.update_one.assert_called_once()
        finally:
            _clear_overrides()

    def test_swipe_up_creates_chapter(self, client: TestClient, mock_db: AsyncMock) -> None:
        """UP swipe creates chapter when 10 fragments accumulated."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "cards": [_make_deck_card()],
            }
        )
        mock_db.story_threads.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "chapters": [],
                "current_fragments": [f"frag{i}" for i in range(9)],  # 9 + 1 = 10
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "card-1", "action": "UP"},
            )
            assert response.status_code == 200
            # Should have called update_one with chapters reset
            call_args = mock_db.story_threads.update_one.call_args
            assert call_args is not None
            update_doc = call_args[0][1]
            assert "chapters" in update_doc["$set"]
            assert update_doc["$set"]["current_fragments"] == []
        finally:
            _clear_overrides()

    def test_swipe_up_already_collected(self, client: TestClient, mock_db: AsyncMock) -> None:
        """UP swipe when card already in collection."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player(collection=["genesis"]))
        mock_db.player_decks.find_one = AsyncMock(
            return_value={"player_id": "test-player", "cards": [_make_deck_card()]}
        )
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "card-1", "action": "UP"},
            )
            assert response.status_code == 200
            assert response.json()["collection_updated"] is False
        finally:
            _clear_overrides()

    def test_swipe_right_knowledge_card(self, client: TestClient, mock_db: AsyncMock) -> None:
        """RIGHT swipe on knowledge card saves to knowledge bank."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "cards": [_make_deck_card(content_type="KNOWLEDGE", text="Cool fact")],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "card-1", "action": "RIGHT"},
            )
            assert response.status_code == 200
            mock_db.knowledge_bank.insert_one.assert_called_once()
        finally:
            _clear_overrides()

    def test_swipe_down_multitype_card(self, client: TestClient, mock_db: AsyncMock) -> None:
        """DOWN swipe on multi-type card awards multiple shard types."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "player_id": "test-player",
                "cards": [_make_deck_card(types=["CREATION", "DESTRUCTION"], shard_yield=2)],
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/swipe",
                json={"player_id": "test-player", "card_id": "card-1", "action": "DOWN"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["shard_changes"]["SOUL"] == 2
            assert data["shard_changes"]["VOID"] == 2
        finally:
            _clear_overrides()


# ── Stage Completion & Milestones ──────────────────────────────────────


class TestStageCompletion:
    def test_complete_stage_no_milestone(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 3})
        try:
            response = client.post("/api/v1/sastahero/stage/1/complete?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["stages_completed"] == 3
            assert data["milestone"] is None
        finally:
            _clear_overrides()

    def test_complete_stage_milestone_5(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 5})
        try:
            response = client.post("/api/v1/sastahero/stage/5/complete?player_id=test-player")
            assert response.status_code == 200
            data = response.json()
            assert data["milestone"] is not None
            assert "shards" in data["milestone"]
        finally:
            _clear_overrides()

    def test_complete_stage_milestone_10(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 10})
        try:
            response = client.post("/api/v1/sastahero/stage/10/complete?player_id=test-player")
            data = response.json()
            assert data["milestone"]["message"] == "10 stages! A rare card awaits next stage."
        finally:
            _clear_overrides()

    def test_complete_stage_milestone_25_badge(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 25})
        try:
            response = client.post("/api/v1/sastahero/stage/25/complete?player_id=test-player")
            data = response.json()
            assert data["milestone"]["badge"] == "explorer_25"
            # Badge should be applied
            mock_db.players.update_one.assert_called()
        finally:
            _clear_overrides()

    def test_complete_stage_milestone_50(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 50})
        try:
            response = client.post("/api/v1/sastahero/stage/50/complete?player_id=test-player")
            data = response.json()
            assert data["milestone"] is not None
        finally:
            _clear_overrides()

    def test_complete_stage_milestone_100(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value={"stages_completed": 100})
        try:
            response = client.post("/api/v1/sastahero/stage/100/complete?player_id=test-player")
            data = response.json()
            assert data["milestone"]["badge"] == "master_100"
            assert "shards" in data["milestone"]
        finally:
            _clear_overrides()

    def test_complete_stage_result_none(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one_and_update = AsyncMock(return_value=None)
        try:
            response = client.post("/api/v1/sastahero/stage/1/complete?player_id=test-player")
            data = response.json()
            assert data["stages_completed"] == 0
        finally:
            _clear_overrides()


# ── Quiz Edge Cases ────────────────────────────────────────────────────


class TestQuizEdgeCases:
    def test_quiz_all_seen_resets(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

        all_seen = [str(i) for i in range(len(QUIZ_QUESTIONS))]
        mock_db.players.find_one = AsyncMock(return_value=_make_player(quiz_seen=all_seen))
        try:
            response = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            assert response.status_code == 200
            # Should have reset seen list
            mock_db.players.update_one.assert_called()
        finally:
            _clear_overrides()

    def test_quiz_invalid_question_id(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": "9999",
                    "selected_index": 0,
                    "time_taken_ms": 5000,
                },
            )
            assert response.status_code == 200
            assert response.json()["correct"] is False
        finally:
            _clear_overrides()

    def test_quiz_streak_bonus(self, client: TestClient, mock_db: AsyncMock) -> None:
        """3 correct in a row triggers bonus card."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(quiz_streak=2)  # next correct = 3
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
                    "time_taken_ms": 10000,
                },
            )
            data = response.json()
            assert data["correct"] is True
            assert data["streak_count"] == 3
            assert data["bonus_card"] is True
        finally:
            _clear_overrides()

    def test_quiz_with_shield_powerup(self, client: TestClient, mock_db: AsyncMock) -> None:
        """Quiz shield preserves streak and awards partial shards on wrong answer."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "QUIZ_SHIELD"}], quiz_streak=2)
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]
            wrong_idx = (correct_idx + 1) % 4

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": wrong_idx,
                    "time_taken_ms": 5000,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["correct"] is False
            # Shield preserves streak
            assert data["streak_count"] == 2
            # 50% partial reward (1 shard)
            assert data["reward_shards"] == 1
        finally:
            _clear_overrides()


# ── All Powerup Purchases ─────────────────────────────────────────────


class TestAllPowerups:
    def test_purchase_peek(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "PEEK"},
            )
            data = response.json()
            assert data["success"] is True
            assert data["shards"]["SOUL"] == 8  # 10 - 2
        finally:
            _clear_overrides()

    def test_purchase_magnetize(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={
                    "player_id": "test-player",
                    "powerup_type": "MAGNETIZE",
                    "shard_type": "SOUL",
                },
            )
            data = response.json()
            assert data["success"] is True
            assert data["shards"]["SOUL"] == 5  # 10 - 5
        finally:
            _clear_overrides()

    def test_purchase_magnetize_no_type_fallback(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """MAGNETIZE without shard_type auto-picks the type with most shards."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "MAGNETIZE"},
            )
            data = response.json()
            assert data["success"] is True
            assert "MAGNETIZE" in data["active_powerups"]
        finally:
            _clear_overrides()

    def test_purchase_magnetize_no_type_insufficient(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """MAGNETIZE without shard_type fails if no type has >= 5."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(
                shards={"SOUL": 4, "SHIELD": 4, "VOID": 4, "LIGHT": 4, "FORCE": 4}
            )
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "MAGNETIZE"},
            )
            assert response.json()["success"] is False
        finally:
            _clear_overrides()

    def test_purchase_quiz_shield(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "QUIZ_SHIELD"},
            )
            data = response.json()
            assert data["success"] is True
            assert data["shards"]["SOUL"] == 6  # 10 - 4
        finally:
            _clear_overrides()

    def test_purchase_lucky_draw(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "LUCKY_DRAW"},
            )
            data = response.json()
            assert data["success"] is True
        finally:
            _clear_overrides()

    def test_purchase_lucky_draw_insufficient(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(
                shards={"SOUL": 3, "SHIELD": 3, "VOID": 0, "LIGHT": 0, "FORCE": 0}
            )
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "LUCKY_DRAW"},
            )
            assert response.json()["success"] is False
        finally:
            _clear_overrides()


# ── Router Edge Cases ──────────────────────────────────────────────────


class TestRouterEdgeCases:
    def test_powerup_missing_fields(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.post("/api/v1/sastahero/powerup", json={})
            assert response.status_code == 422
        finally:
            _clear_overrides()

    def test_reroll_missing_fields(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        try:
            response = client.post("/api/v1/sastahero/reroll", json={})
            assert response.status_code == 422
        finally:
            _clear_overrides()

    def test_reroll_no_powerup(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/reroll",
                json={"player_id": "test-player", "card_id": "card-1"},
            )
            assert response.status_code == 400
        finally:
            _clear_overrides()

    def test_reroll_success(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "REROLL"}])
        )
        mock_db.player_decks.find_one = AsyncMock(
            return_value={
                "_id": "deck-id",
                "player_id": "test-player",
                "cards": [_make_deck_card()],
                "completed": False,
            }
        )
        try:
            response = client.post(
                "/api/v1/sastahero/reroll",
                json={"player_id": "test-player", "card_id": "card-1"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "card_id" in data
            assert "name" in data
        finally:
            _clear_overrides()

    def test_reroll_deck_not_found(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "REROLL"}])
        )
        mock_db.player_decks.find_one = AsyncMock(return_value=None)
        try:
            response = client.post(
                "/api/v1/sastahero/reroll",
                json={"player_id": "test-player", "card_id": "card-1"},
            )
            assert response.status_code == 400
        finally:
            _clear_overrides()


# ── Knowledge with Category Filter ────────────────────────────────────


class TestKnowledgeFilter:
    def test_knowledge_with_category(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.knowledge_bank.find = lambda *_a, **_k: _SortableCursorMock(
            [
                {
                    "player_id": "test-player",
                    "text": "Science fact",
                    "category": "science",
                    "saved_at": "2026-03-18T00:00:00Z",
                }
            ]
        )
        mock_db.knowledge_bank.distinct = AsyncMock(return_value=["science"])
        try:
            response = client.get(
                "/api/v1/sastahero/knowledge?player_id=test-player&category=science"
            )
            assert response.status_code == 200
            assert response.json()["total"] == 1
        finally:
            _clear_overrides()


# ── Extend Pool TTL ───────────────────────────────────────────────────


class TestExtendPoolTTL:
    @pytest.mark.asyncio
    async def test_extend_ttl(self, mock_db: AsyncMock) -> None:
        from app.modules.sastahero.services import extend_pool_ttl

        await extend_pool_ttl(mock_db, "genesis")
        mock_db.card_pool.update_one.assert_called_once()


# ── P0 Fix Tests ──────────────────────────────────────────────────────


class TestQuizTimeoutFix:
    """Fix 1: Quiz timeout (selected_index=-1) should award zero shards."""

    def test_timeout_awards_zero_shards(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player(quiz_streak=3))
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": -1,
                    "time_taken_ms": 15000,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["correct"] is False
            assert data["reward_shards"] == 0
            assert data["streak_count"] == 0
            assert data["bonus_card"] is False
        finally:
            _clear_overrides()

    def test_timeout_resets_streak(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player(quiz_streak=5))
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

            response = client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": -1,
                    "time_taken_ms": 16000,
                },
            )
            data = response.json()
            assert data["streak_count"] == 0
        finally:
            _clear_overrides()


class TestQuizShieldFix:
    """Fix 2: Quiz Shield should preserve streak and award partial shards."""

    def test_shield_preserves_streak_on_wrong(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "QUIZ_SHIELD"}], quiz_streak=4)
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

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
            data = response.json()
            assert data["correct"] is False
            assert data["streak_count"] == 4  # preserved
            assert data["reward_shards"] == 1  # 50% partial
        finally:
            _clear_overrides()

    def test_shield_consumed_after_use(self, client: TestClient, mock_db: AsyncMock) -> None:
        """After shield absorbs a wrong answer, it should be removed from powerups."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "QUIZ_SHIELD"}], quiz_streak=2)
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]
            wrong_idx = (correct_idx + 1) % 4

            client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": wrong_idx,
                    "time_taken_ms": 8000,
                },
            )
            # Check the DB update removed the shield
            update_call = mock_db.players.update_one.call_args
            assert update_call is not None
            set_doc = update_call[0][1]["$set"]
            assert "active_powerups" in set_doc
            shield_types = [p.get("type") for p in set_doc["active_powerups"]]
            assert "QUIZ_SHIELD" not in shield_types
        finally:
            _clear_overrides()

    def test_shield_not_consumed_on_correct(self, client: TestClient, mock_db: AsyncMock) -> None:
        """Shield should NOT be consumed when answer is correct."""
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(active_powerups=[{"type": "QUIZ_SHIELD"}], quiz_streak=0)
        )
        try:
            quiz_resp = client.get("/api/v1/sastahero/quiz?player_id=test-player")
            q_id = quiz_resp.json()["question_id"]

            from app.modules.sastahero.seed.quiz_data import QUIZ_QUESTIONS

            _, _, correct_idx, _, _ = QUIZ_QUESTIONS[int(q_id)]

            client.post(
                "/api/v1/sastahero/quiz/answer",
                json={
                    "player_id": "test-player",
                    "question_id": q_id,
                    "selected_index": correct_idx,
                    "time_taken_ms": 8000,
                },
            )
            update_call = mock_db.players.update_one.call_args
            set_doc = update_call[0][1]["$set"]
            shield_types = [p.get("type") for p in set_doc["active_powerups"]]
            assert "QUIZ_SHIELD" in shield_types
        finally:
            _clear_overrides()


class TestMagnetizeFallbackFix:
    """Fix 3: MAGNETIZE without shard_type should auto-pick the highest balance type."""

    def test_magnetize_picks_highest_shard(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(
                shards={"SOUL": 2, "SHIELD": 3, "VOID": 8, "LIGHT": 1, "FORCE": 0}
            )
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "MAGNETIZE"},
            )
            data = response.json()
            assert data["success"] is True
            # VOID had 8, should have been deducted by 5
            assert data["shards"]["VOID"] == 3
        finally:
            _clear_overrides()

    def test_magnetize_explicit_type_still_works(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(
            return_value=_make_player(
                shards={"SOUL": 10, "SHIELD": 10, "VOID": 10, "LIGHT": 10, "FORCE": 10}
            )
        )
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={
                    "player_id": "test-player",
                    "powerup_type": "MAGNETIZE",
                    "shard_type": "SHIELD",
                },
            )
            data = response.json()
            assert data["success"] is True
            assert data["shards"]["SHIELD"] == 5

        finally:
            _clear_overrides()


class TestPeekPreviewFix:
    """Fix 4: PEEK should return preview cards."""

    def test_peek_returns_preview(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "PEEK"},
            )
            data = response.json()
            assert data["success"] is True
            assert data["peek_preview"] is not None
            assert len(data["peek_preview"]) == 3
            for card in data["peek_preview"]:
                assert "card_id" in card
                assert "identity_id" in card
                assert "name" in card
                assert "rarity" in card
        finally:
            _clear_overrides()

    def test_peek_preview_null_when_not_peek(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "REROLL"},
            )
            data = response.json()
            assert data["success"] is True
            assert data["peek_preview"] is None
        finally:
            _clear_overrides()

    def test_peek_preview_cards_are_distinct(self, client: TestClient, mock_db: AsyncMock) -> None:
        _override_db(mock_db)
        mock_db.players.find_one = AsyncMock(return_value=_make_player())
        try:
            response = client.post(
                "/api/v1/sastahero/powerup",
                json={"player_id": "test-player", "powerup_type": "PEEK"},
            )
            data = response.json()
            ids = [c["identity_id"] for c in data["peek_preview"]]
            assert len(ids) == len(set(ids))  # no duplicates
        finally:
            _clear_overrides()
