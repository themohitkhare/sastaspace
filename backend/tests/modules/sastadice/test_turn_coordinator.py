"""Tests for TurnCoordinator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.sastadice.schemas import (
    ChaosLevel,
    GameSession,
    GameSettings,
    GameStatus,
    Player,
    Tile,
    TileType,
    TurnPhase,
    WinCondition,
)
from app.modules.sastadice.services.turn_coordinator import TurnCoordinator


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = MagicMock()
    repo.update = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_position = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.save_board = AsyncMock()
    return repo


@pytest.fixture
def mock_turn_manager():
    """Create a mock turn manager."""
    manager = MagicMock()
    manager.calculate_go_bonus = MagicMock(return_value=200)
    return manager


@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    settings = GameSettings(
        win_condition=WinCondition.SUDDEN_DEATH,
        round_limit=30,
        target_cash=10000,
        starting_cash_multiplier=1.0,
        go_bonus_base=200,
        go_inflation_per_round=20,
        chaos_level=ChaosLevel.NORMAL,
    )
    return GameSession(
        id="test-game",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.PRE_ROLL,
        players=[],
        board=[Tile(id="tile0", type=TileType.GO, name="GO", position=0)],
        settings=settings,
        current_round=1,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
        current_turn_player_id="player1",
    )


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(
        id="player1",
        name="Test Player",
        cash=1500,
        position=0,
        is_bankrupt=False,
        in_jail=False,
    )


@pytest.fixture
def coordinator(mock_repository, mock_turn_manager):
    """Create a TurnCoordinator instance."""
    return TurnCoordinator(mock_repository, mock_turn_manager)


class TestTurnCoordinator:
    """Test suite for TurnCoordinator."""

    @pytest.mark.asyncio
    async def test_validate_roll_dice_success(self, coordinator, sample_game, sample_player):
        """Test successful dice roll validation."""
        sample_game.players = [sample_player]
        is_valid, error, player = await coordinator._validate_roll_dice(sample_game, "player1")
        assert is_valid is True
        assert error is None
        assert player == sample_player

    @pytest.mark.asyncio
    async def test_validate_roll_dice_wrong_status(self, coordinator, sample_game):
        """Test validation fails when game is not ACTIVE."""
        sample_game.status = GameStatus.LOBBY
        is_valid, error, player = await coordinator._validate_roll_dice(sample_game, "player1")
        assert is_valid is False
        assert "ACTIVE" in error

    @pytest.mark.asyncio
    async def test_validate_roll_dice_wrong_turn(self, coordinator, sample_game):
        """Test validation fails when it's not player's turn."""
        is_valid, error, player = await coordinator._validate_roll_dice(sample_game, "player2")
        assert is_valid is False
        assert "Not your turn" in error

    @pytest.mark.asyncio
    async def test_validate_roll_dice_wrong_phase(self, coordinator, sample_game, sample_player):
        """Test validation fails when turn phase is wrong."""
        sample_game.players = [sample_player]
        sample_game.turn_phase = TurnPhase.DECISION
        is_valid, error, player = await coordinator._validate_roll_dice(sample_game, "player1")
        assert is_valid is False
        assert "turn phase" in error

    @pytest.mark.asyncio
    async def test_handle_jail_roll_released(
        self, coordinator, sample_game, sample_player, mock_repository
    ):
        """Test jail roll when player is released."""
        sample_game.players = [sample_player]
        sample_player.in_jail = True
        sample_player.jail_turns = 0

        async def send_to_jail(game, player):
            pass

        result = await coordinator._handle_jail_roll(sample_game, sample_player, send_to_jail)
        assert result is None
        assert sample_player.in_jail is False
        assert sample_player.jail_turns == 0

    @pytest.mark.asyncio
    async def test_handle_jail_roll_stuck(
        self, coordinator, sample_game, sample_player, mock_repository
    ):
        """Test jail roll when player is still stuck."""
        sample_game.players = [sample_player]
        sample_player.in_jail = True
        sample_player.jail_turns = -1

        async def send_to_jail(game, player):
            pass

        result = await coordinator._handle_jail_roll(sample_game, sample_player, send_to_jail)
        assert result is not None
        assert result.dice1 == 0
        assert result.dice2 == 0
        assert sample_game.turn_phase == TurnPhase.POST_TURN

    @pytest.mark.asyncio
    async def test_handle_movement_passed_go(
        self, coordinator, sample_game, sample_player, mock_turn_manager, mock_repository
    ):
        """Test movement when player passes GO."""
        sample_game.players = [sample_player]
        sample_player.position = 35
        mock_turn_manager.calculate_go_bonus.return_value = 200

        passed_go = await coordinator._handle_movement(
            sample_game, sample_player, "player1", 10, False
        )
        assert passed_go is True
        assert sample_player.cash == 1700
        mock_repository.update_player_cash.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_movement_no_go(
        self, coordinator, sample_game, sample_player, mock_repository
    ):
        """Test movement when player doesn't pass GO."""
        sample_game.players = [sample_player]
        sample_game.board = [
            Tile(id=f"tile{i}", type=TileType.PROPERTY, name=f"Tile {i}", position=i)
            for i in range(20)
        ]
        sample_player.position = 5

        passed_go = await coordinator._handle_movement(
            sample_game, sample_player, "player1", 5, False
        )
        assert passed_go is False
        assert sample_player.position == 10
        mock_repository.update_player_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_doubles_replay(
        self, coordinator, sample_game, sample_player, mock_repository
    ):
        """Test doubles replay logic."""
        sample_game.players = [sample_player]
        sample_game.last_dice_roll = {"is_doubles": True}

        result = await coordinator._check_doubles_replay(sample_game, sample_player)
        assert result is not None
        assert result.success is True
        assert "Doubles" in result.message or "DOUBLES" in result.message

    @pytest.mark.asyncio
    async def test_check_doubles_replay_no_doubles(self, coordinator, sample_game, sample_player):
        """Test doubles replay when no doubles."""
        sample_game.players = [sample_player]
        sample_game.last_dice_roll = {"is_doubles": False}

        result = await coordinator._check_doubles_replay(sample_game, sample_player)
        assert result is None

    @pytest.mark.asyncio
    async def test_advance_to_next_player(self, coordinator, sample_game):
        """Test advancing to next player."""
        player1 = Player(id="player1", name="Player 1", cash=1500, position=0, is_bankrupt=False)
        player2 = Player(id="player2", name="Player 2", cash=1500, position=0, is_bankrupt=False)
        sample_game.players = [player1, player2]
        sample_game.current_turn_player_id = "player1"

        next_player, old_round = await coordinator._advance_to_next_player(sample_game)
        assert next_player.id == "player2"
        assert old_round == 1

    @pytest.mark.asyncio
    async def test_advance_to_next_player_sets_first_player(self, coordinator, sample_game):
        """Test that first_player_id is set on first advance."""
        player1 = Player(id="player1", name="Player 1", cash=1500, position=0, is_bankrupt=False)
        player2 = Player(id="player2", name="Player 2", cash=1500, position=0, is_bankrupt=False)
        sample_game.players = [player1, player2]
        sample_game.current_turn_player_id = "player1"
        sample_game.first_player_id = None

        next_player, old_round = await coordinator._advance_to_next_player(sample_game)
        assert sample_game.first_player_id == "player1"

    @pytest.mark.asyncio
    async def test_increment_round_if_needed(self, coordinator, sample_game):
        """Test round increment when returning to first player."""
        player1 = Player(id="player1", name="Player 1", cash=1500, position=0, is_bankrupt=False)
        player2 = Player(id="player2", name="Player 2", cash=1500, position=0, is_bankrupt=False)
        sample_game.players = [player1, player2]
        sample_game.current_turn_player_id = "player2"
        sample_game.first_player_id = "player1"
        sample_game.current_round = 1

        async def check_sudden_death(game):
            return None

        result = await coordinator._increment_round_if_needed(
            sample_game, player1, 1, check_sudden_death
        )
        assert result is None
        assert sample_game.current_round == 2

    @pytest.mark.asyncio
    async def test_check_sudden_death_triggered(self, coordinator, sample_game, mock_repository):
        """Test sudden death condition."""
        sample_game.settings.win_condition = WinCondition.SUDDEN_DEATH
        sample_game.settings.round_limit = 5
        sample_game.current_round = 5
        player1 = Player(id="player1", name="Player 1", cash=2000, position=0, is_bankrupt=False)
        sample_game.players = [player1]

        def determine_winner(game):
            return {"name": "Player 1", "cash": 2000}

        result = await coordinator._check_sudden_death(sample_game, determine_winner)
        assert result is not None
        assert result.success is True
        assert "SUDDEN DEATH" in result.message
        assert sample_game.status == GameStatus.FINISHED
