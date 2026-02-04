from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.sastadice.schemas import (
    ActionType,
    ChaosConfig,
    GameSession,
    GameSettings,
    GameStatus,
    Player,
    Tile,
    TileType,
    TurnPhase,
)
from app.modules.sastadice.services.simulation_manager import SimulationManager


@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_dispatcher():
    dispatcher = AsyncMock()
    dispatcher.dispatch = AsyncMock()
    # Return a dummy result object with a message
    success_result = MagicMock()
    success_result.message = "OK"
    success_result.data = {}
    dispatcher.dispatch.return_value = success_result
    return dispatcher


@pytest.fixture
def simulation_manager(mock_repository, mock_dispatcher):
    return SimulationManager(
        repository=mock_repository,
        action_dispatcher=mock_dispatcher,
        get_game_callback=AsyncMock(),
        start_game_callback=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_advance_if_bankrupt_current(simulation_manager, mock_repository):
    """Test that turn advances if current player is bankrupt."""
    # Setup players
    p1 = Player(id="p1", name="P1", cash=-100, is_bankrupt=True)
    p2 = Player(id="p2", name="P2", cash=1000)
    p3 = Player(id="p3", name="P3", cash=1000)

    # Setup game
    game = GameSession(
        id="game1",
        status=GameStatus.ACTIVE,
        players=[p1, p2, p3],
        current_turn_player_id="p1",
        turn_phase=TurnPhase.POST_TURN,
        board=[],
        settings=GameSettings(),
    )

    # Mock get_game to return our game
    simulation_manager._get_game.return_value = game

    # Execute
    await simulation_manager._advance_if_bankrupt_current("game1")

    # Verify
    # Should have updated game to next valid player (p2)
    assert game.current_turn_player_id == "p2"
    assert game.turn_phase == TurnPhase.PRE_ROLL
    assert game.pending_decision is None

    # Verify update was called
    mock_repository.update.assert_called_once_with(game)


@pytest.mark.asyncio
async def test_advance_if_bankrupt_current_no_active_players(simulation_manager, mock_repository):
    """Test verification when everyone is bankrupt (edge case)."""
    p1 = Player(id="p1", name="P1", cash=-100, is_bankrupt=True)
    p2 = Player(id="p2", name="P2", cash=-100, is_bankrupt=True)

    game = GameSession(
        id="game1",
        status=GameStatus.ACTIVE,
        players=[p1, p2],
        current_turn_player_id="p1",
        turn_phase=TurnPhase.POST_TURN,
        board=[],
        settings=GameSettings(),
    )

    simulation_manager._get_game.return_value = game

    await simulation_manager._advance_if_bankrupt_current("game1")

    # Should not crash, and not update anything (since no active players found)
    # The logic returns early if `not active`
    mock_repository.update.assert_not_called()


@pytest.mark.asyncio
async def test_attempt_cpu_trade_proposal_ignores_bankrupt_targets(
    simulation_manager, mock_dispatcher
):
    """Test that CPU does not propose trades to bankrupt players."""
    p1 = Player(id="p1", name="P1", cash=1000)
    p2_bankrupt = Player(id="p2", name="P2", cash=-100, is_bankrupt=True)

    # Property for P1 so they have something to trade
    prop1 = Tile(id="t1", name="Prop 1", type=TileType.PROPERTY, owner_id="p1", price=100)

    game = GameSession(
        id="game1",
        status=GameStatus.ACTIVE,
        players=[p1, p2_bankrupt],
        current_turn_player_id="p1",
        board=[prop1],
        settings=GameSettings(),
    )

    turn_info = {"actions": []}
    coverage = {}

    # Force random checks to pass for "decision so make trade" but fail for "randomly skip"
    # The function has:
    # if random.random() >= 0.1: return  (needs < 0.1)
    # ...
    # We want it to proceed but find NO targets.

    with patch("random.random", side_effect=lambda: 0.05):  # Always small enough to proceed
        await simulation_manager._attempt_cpu_trade_proposal(game, p1, turn_info, coverage)

    # Should NOT have dispatched PROPOSE_TRADE because p2 is bankrupt -> potential_targets empty
    assert len(mock_dispatcher.dispatch.mock_calls) == 0
    assert "PROPOSE_TRADE" not in coverage


@pytest.mark.asyncio
async def test_attempt_cpu_trade_proposal_valid_target(simulation_manager, mock_dispatcher):
    """Test that CPU proposes trades to active players."""
    p1 = Player(id="p1", name="P1", cash=1000)
    p2 = Player(id="p2", name="P2", cash=1000)

    prop1 = Tile(id="t1", name="Prop 1", type=TileType.PROPERTY, owner_id="p1", price=100)
    prop2 = Tile(id="t2", name="Prop 2", type=TileType.PROPERTY, owner_id="p2", price=100)

    game = GameSession(
        id="game1",
        status=GameStatus.ACTIVE,
        players=[p1, p2],
        current_turn_player_id="p1",
        board=[prop1, prop2],
        settings=GameSettings(),
    )

    turn_info = {"actions": []}
    coverage = {}

    # We need to control random choices to ensure a trade is constructed
    # Flows:
    # 1. random() < 0.1 -> passes (returns 0.0)
    # 2. random.choice(potential_targets) -> returns p2
    # 3. random.choice(my_props) (if cond) -> returns prop1
    # 4. random.choice(their_props) (if cond) -> returns prop2
    # 5. offer_cash calc...

    # Use side_effect for random.random to control flow
    # random calls:
    # 1. >= 0.1 check (need false, so < 0.1) -> 0.0
    # 2. offer_props check (<0.5) -> 0.0
    # 3. req_props check (<0.5) -> 0.0
    # 4. offer_cash check (<0.5) -> 0.0

    with patch("random.random", return_value=0.0), patch("random.choice") as mock_choice:
        mock_choice.side_effect = [p2, prop1, prop2]  # Target, My Prop, Their Prop

        await simulation_manager._attempt_cpu_trade_proposal(game, p1, turn_info, coverage)

    # Verify dispatch called
    mock_dispatcher.dispatch.assert_called_once()
    args, kwargs = mock_dispatcher.dispatch.call_args
    assert args[2] == ActionType.PROPOSE_TRADE  # args[0]=game, args[1]=p_id, args[2]=action
    assert "PROPOSE_TRADE" in coverage


@pytest.mark.asyncio
async def test_monkey_mode_bidding(mock_repository, mock_dispatcher):
    """Test that Monkey Mode triggers overbidding."""
    # Setup
    config = ChaosConfig(chaos_probability=1.0)  # Always trigger
    manager = SimulationManager(
        repository=mock_repository,
        action_dispatcher=mock_dispatcher,
        get_game_callback=AsyncMock(),
        start_game_callback=AsyncMock(),
        chaos_config=config,
    )

    p1 = Player(id="p1", name="P1", cash=5000)
    game = GameSession(id="g1", status=GameStatus.ACTIVE, players=[p1], current_turn_player_id="p1")
    game.auction_state = MagicMock()
    game.auction_state.end_time = 9999999999
    game.auction_state.participants = ["p1"]
    game.auction_state.highest_bid = 100
    game.auction_state.min_bid_increment = 10
    game.turn_phase = TurnPhase.AUCTION

    manager._get_game.return_value = game
    turn_info = {"actions": []}
    coverage = {}

    # Execute
    await manager._execute_simulated_turn("g1", p1, turn_info, coverage)

    # Assert
    # Should have called BID with high amount (Monkey Bid)
    # We look for "MONKEY_BID" in coverage
    assert "MONKEY_BID" in coverage
    # Verify dispatch called with BID
    calls = [c for c in mock_dispatcher.dispatch.mock_calls if c.args[2] == ActionType.BID]
    assert len(calls) > 0
    # Verify bid amount is > normal min bid (110)
    bid_call = calls[0]
    bid_amount = bid_call.args[3]["amount"]
    assert bid_amount > 110  # Monkey adds 5-20 increments


@pytest.mark.asyncio
async def test_monkey_mode_trade_spam(mock_repository, mock_dispatcher):
    """Test that Monkey Mode spams bad trades."""
    config = ChaosConfig(chaos_probability=1.0)
    manager = SimulationManager(
        repository=mock_repository,
        action_dispatcher=mock_dispatcher,
        get_game_callback=AsyncMock(),
        start_game_callback=AsyncMock(),
        chaos_config=config,
    )

    p1 = Player(id="p1", name="P1", cash=1000)
    p2 = Player(id="p2", name="P2", cash=1000)
    target_prop = Tile(
        id="t1", name="Target Prop", type=TileType.PROPERTY, owner_id="p2", price=200
    )

    game = GameSession(
        id="g1",
        status=GameStatus.ACTIVE,
        players=[p1, p2],
        current_turn_player_id="p1",
        board=[target_prop],
    )
    manager._get_game.return_value = game

    turn_info = {"actions": []}
    coverage = {}

    # Patch random to ensure logic hits
    with patch("random.random", return_value=0.0):  # Pass probability checks
        with patch("random.choice", side_effect=[p2, "t1"]):  # Choose p2 then t1
            await manager._attempt_cpu_trade_proposal(game, p1, turn_info, coverage)

    assert "MONKEY_TRADE_SPAM" in coverage
    calls = [
        c for c in mock_dispatcher.dispatch.mock_calls if c.args[2] == ActionType.PROPOSE_TRADE
    ]
    assert len(calls) > 0
    payload = calls[0].args[3]
    assert payload["offer_cash"] == 1  # Monkey offer
    assert payload["req_props"][0] == "t1"
