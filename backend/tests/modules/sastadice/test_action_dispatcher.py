"""Tests for ActionDispatcher — targeting coverage of all major action handlers."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.sastadice.schemas import (
    ActionResult,
    ActionType,
    AuctionState,
    GameSession,
    GameSettings,
    GameStatus,
    PendingDecision,
    Player,
    Tile,
    TileType,
    TradeOffer,
    TurnPhase,
    WinCondition,
)
from app.modules.sastadice.services.action_dispatcher import ActionDispatcher

# ============================================================
# Helper builders
# ============================================================


def make_settings(**kwargs: object) -> GameSettings:
    defaults: dict[str, object] = {
        "win_condition": WinCondition.SUDDEN_DEATH,
        "round_limit": 30,
        "enable_auctions": True,
        "enable_upgrades": True,
        "enable_trading": True,
        "jail_bribe_cost": 50,
        "target_cash": 10000,
    }
    defaults.update(kwargs)
    return GameSettings(**defaults)  # type: ignore[arg-type]


def make_game(**kwargs: object) -> GameSession:
    defaults: dict[str, object] = {
        "id": "game-1",
        "status": GameStatus.ACTIVE,
        "turn_phase": TurnPhase.PRE_ROLL,
        "players": [],
        "board": [],
        "settings": make_settings(),
        "current_round": 1,
        "rent_multiplier": 1.0,
        "blocked_tiles": [],
        "event_deck": list(range(10)),
        "used_event_deck": [],
        "active_trade_offers": [],
        "bankruptcy_auction_queue": [],
    }
    defaults.update(kwargs)
    return GameSession(**defaults)  # type: ignore[arg-type]


def make_player(
    pid: str = "p1",
    name: str = "Alice",
    cash: int = 1000,
    position: int = 0,
    properties: list[str] | None = None,
    active_buff: str | None = None,
    in_jail: bool = False,
    jail_turns: int = 0,
    is_bankrupt: bool = False,
) -> Player:
    return Player(
        id=pid,
        name=name,
        cash=cash,
        position=position,
        color="#FF0000",
        properties=properties or [],
        ready=True,
        active_buff=active_buff,
        in_jail=in_jail,
        jail_turns=jail_turns,
        is_bankrupt=is_bankrupt,
    )


def make_tile(
    tid: str = "tile-1",
    name: str = "Test Property",
    tile_type: TileType = TileType.PROPERTY,
    position: int = 1,
    price: int = 200,
    rent: int = 20,
    color: str | None = "RED",
    owner_id: str | None = None,
    upgrade_level: int = 0,
) -> Tile:
    return Tile(
        id=tid,
        type=tile_type,
        name=name,
        position=position,
        price=price,
        rent=rent,
        color=color,
        owner_id=owner_id,
        upgrade_level=upgrade_level,
    )


def make_mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.update = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_properties = AsyncMock()
    repo.update_player_buff = AsyncMock()
    repo.update_player_bankrupt = AsyncMock()
    repo.update_player_jail = AsyncMock()
    repo.update_player_position = AsyncMock()
    repo.update_tile_owner = AsyncMock()
    repo.save_board = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


def make_dispatcher(
    repo: MagicMock | None = None,
    economy_manager: MagicMock | None = None,
    auction_manager: MagicMock | None = None,
    trade_manager: MagicMock | None = None,
    turn_coordinator: MagicMock | None = None,
    turn_manager: MagicMock | None = None,
    jail_manager: MagicMock | None = None,
    roll_dice_callback: object = None,
    handle_tile_landing_callback: object = None,
    send_to_jail_callback: object = None,
) -> ActionDispatcher:
    repo = repo or make_mock_repo()
    economy_manager = economy_manager or MagicMock()
    auction_manager = auction_manager or MagicMock()
    trade_manager = trade_manager or MagicMock()
    turn_coordinator = turn_coordinator or MagicMock()
    turn_manager = turn_manager or MagicMock()

    return ActionDispatcher(
        repository=repo,
        economy_manager=economy_manager,
        auction_manager=auction_manager,
        trade_manager=trade_manager,
        turn_coordinator=turn_coordinator,
        turn_manager=turn_manager,
        jail_manager=jail_manager,
        roll_dice_callback=roll_dice_callback,
        handle_tile_landing_callback=handle_tile_landing_callback,
        send_to_jail_callback=send_to_jail_callback,
    )


# ============================================================
# _validate_payload tests
# ============================================================


class TestValidatePayload:
    def test_bid_missing_amount(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.BID, {})
        assert not ok
        assert err == "Bid amount required"

    def test_bid_negative_amount(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.BID, {"amount": -5})
        assert not ok
        assert err is not None

    def test_bid_valid(self) -> None:
        d = make_dispatcher()
        ok, validated, err = d._validate_payload(ActionType.BID, {"amount": 100})
        assert ok
        assert err is None
        assert validated["amount"] == 100

    def test_upgrade_missing_tile_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.UPGRADE, {})
        assert not ok
        assert "tile_id" in (err or "")

    def test_upgrade_non_string_tile_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.UPGRADE, {"tile_id": 42})
        assert not ok

    def test_upgrade_valid(self) -> None:
        d = make_dispatcher()
        ok, validated, _ = d._validate_payload(ActionType.UPGRADE, {"tile_id": "t-1"})
        assert ok

    def test_downgrade_missing_tile_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.DOWNGRADE, {})
        assert not ok

    def test_buy_buff_missing_buff_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.BUY_BUFF, {})
        assert not ok
        assert "buff_id" in (err or "")

    def test_buy_buff_non_string_buff_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.BUY_BUFF, {"buff_id": 99})
        assert not ok

    def test_propose_trade_missing_target_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.PROPOSE_TRADE, {})
        assert not ok
        assert "target_id" in (err or "")

    def test_propose_trade_non_string_target_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.PROPOSE_TRADE, {"target_id": 1})
        assert not ok

    def test_accept_trade_missing_trade_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.ACCEPT_TRADE, {})
        assert not ok
        assert "trade_id" in (err or "")

    def test_decline_trade_non_string_trade_id(self) -> None:
        d = make_dispatcher()
        ok, _, err = d._validate_payload(ActionType.DECLINE_TRADE, {"trade_id": 123})
        assert not ok

    def test_cancel_trade_valid(self) -> None:
        d = make_dispatcher()
        ok, validated, _ = d._validate_payload(ActionType.CANCEL_TRADE, {"trade_id": "t-1"})
        assert ok


# ============================================================
# dispatch — invalid payload short-circuit
# ============================================================


class TestDispatchValidationShortCircuit:
    async def test_dispatch_rejects_invalid_payload(self) -> None:
        d = make_dispatcher()
        game = make_game()
        result = await d.dispatch(game, "p1", ActionType.BID, {})  # missing amount
        assert result.success is False
        assert "Bid amount" in result.message

    async def test_dispatch_unknown_action_falls_through(self) -> None:
        # This tests the `case _:` fallback — we use a real ActionType that has
        # no dedicated handler by patching to reach default.
        # PEEK_EVENTS has no dedicated case so it hits the default.
        d = make_dispatcher()
        game = make_game()
        result = await d.dispatch(game, "p1", ActionType.PEEK_EVENTS, {})
        assert result.success is False
        assert "Unknown action" in result.message


# ============================================================
# _handle_buy_property
# ============================================================


class TestHandleBuyProperty:
    async def test_not_your_turn(self) -> None:
        game = make_game(current_turn_player_id="p2")
        d = make_dispatcher()
        result = await d._handle_buy_property(game, "p1")
        assert not result.success
        assert "Not your turn" in result.message

    async def test_buy_success(self) -> None:
        repo = make_mock_repo()
        economy_manager = MagicMock()
        economy_manager.handle_buy_property = AsyncMock(
            return_value=(True, "Bought 'Test' for $200!", "Test", 200)
        )
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher(repo=repo, economy_manager=economy_manager)
        result = await d._handle_buy_property(game, "p1")
        assert result.success
        repo.update.assert_awaited_once()

    async def test_buy_failure_returns_message(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_buy_property = AsyncMock(
            return_value=(False, "Not enough cash", None, None)
        )
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d._handle_buy_property(game, "p1")
        assert not result.success
        assert "Not enough cash" in result.message


# ============================================================
# _handle_pass_property
# ============================================================


class TestHandlePassProperty:
    async def test_not_your_turn(self) -> None:
        game = make_game(current_turn_player_id="p2")
        d = make_dispatcher()
        result = await d._handle_pass_property(game, "p1")
        assert not result.success
        assert "Not your turn" in result.message

    async def test_wrong_phase(self) -> None:
        game = make_game(current_turn_player_id="p1", turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d._handle_pass_property(game, "p1")
        assert not result.success
        assert "Cannot pass" in result.message

    async def test_pass_starts_auction_for_unowned_property(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.start_auction = MagicMock()
        tile = make_tile("tile-1", owner_id=None)
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.DECISION,
            board=[tile],
            pending_decision=PendingDecision(type="BUY", tile_id="tile-1", price=200),
        )
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._handle_pass_property(game, "p1")
        assert result.success
        auction_manager.start_auction.assert_called_once()

    async def test_pass_no_tile_id_in_decision(self) -> None:
        repo = make_mock_repo()
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.DECISION,
            pending_decision=PendingDecision(type="BUY", tile_id=None, price=0),
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_pass_property(game, "p1")
        assert result.success
        assert game.turn_phase == TurnPhase.POST_TURN

    async def test_pass_auction_disabled_goes_to_post_turn(self) -> None:
        repo = make_mock_repo()
        settings = make_settings(enable_auctions=False)
        tile = make_tile("tile-1", owner_id=None)
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.DECISION,
            board=[tile],
            settings=settings,
            pending_decision=PendingDecision(type="BUY", tile_id="tile-1", price=200),
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_pass_property(game, "p1")
        assert result.success
        assert game.turn_phase == TurnPhase.POST_TURN


# ============================================================
# _handle_bid
# ============================================================


class TestHandleBid:
    async def test_no_active_auction(self) -> None:
        game = make_game(turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d._handle_bid(game, "p1", {"amount": 100})
        assert not result.success
        assert "No active auction" in result.message

    async def test_bid_amount_zero(self) -> None:
        auction = AuctionState(
            property_id="tile-1",
            highest_bid=0,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=["p1"],
        )
        game = make_game(turn_phase=TurnPhase.AUCTION, auction_state=auction)
        auction_manager = MagicMock()
        auction_manager.check_auction_timeout = MagicMock(return_value=False)
        d = make_dispatcher(auction_manager=auction_manager)
        result = await d._handle_bid(game, "p1", {"amount": 0})
        assert not result.success

    async def test_bid_timeout_resolves_auction(self) -> None:
        repo = make_mock_repo()
        auction = AuctionState(
            property_id="tile-1",
            highest_bid=100,
            highest_bidder_id="p1",
            start_time=time.time() - 60,
            end_time=time.time() - 1,
            participants=["p1"],
        )
        player = make_player("p1", cash=500)
        tile = make_tile("tile-1")
        game = make_game(
            turn_phase=TurnPhase.AUCTION,
            auction_state=auction,
            players=[player],
            board=[tile],
        )
        auction_manager = MagicMock()
        auction_manager.check_auction_timeout = MagicMock(return_value=True)
        auction_manager.resolve_auction = MagicMock(
            return_value=(True, "Sold!", "p1", 100, "tile-1")
        )
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._handle_bid(game, "p1", {"amount": 200})
        assert result.success

    async def test_bid_placed_successfully(self) -> None:
        repo = make_mock_repo()
        auction = AuctionState(
            property_id="tile-1",
            highest_bid=0,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=["p1"],
        )
        game = make_game(turn_phase=TurnPhase.AUCTION, auction_state=auction)
        auction_manager = MagicMock()
        auction_manager.check_auction_timeout = MagicMock(return_value=False)
        auction_manager.place_bid = MagicMock(return_value=(True, "Bid placed"))
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._handle_bid(game, "p1", {"amount": 150})
        assert result.success
        repo.update.assert_awaited_once()

    async def test_bid_rejected_by_auction_manager(self) -> None:
        auction = AuctionState(
            property_id="tile-1",
            highest_bid=200,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=["p1"],
        )
        game = make_game(turn_phase=TurnPhase.AUCTION, auction_state=auction)
        auction_manager = MagicMock()
        auction_manager.check_auction_timeout = MagicMock(return_value=False)
        auction_manager.place_bid = MagicMock(return_value=(False, "Bid too low"))
        d = make_dispatcher(auction_manager=auction_manager)
        result = await d._handle_bid(game, "p1", {"amount": 100})
        assert not result.success


# ============================================================
# _handle_upgrade
# ============================================================


class TestHandleUpgrade:
    async def test_upgrade_success_updates_message(self) -> None:
        repo = make_mock_repo()
        economy_manager = MagicMock()
        economy_manager.handle_upgrade = AsyncMock(
            return_value=(True, "Upgraded!", "Script Kiddie")
        )
        player = make_player("p1")
        tile = make_tile("tile-1")
        game = make_game(players=[player], board=[tile])
        turn_manager = MagicMock()
        d = make_dispatcher(repo=repo, economy_manager=economy_manager, turn_manager=turn_manager)
        result = await d._handle_upgrade(game, "p1", {"tile_id": "tile-1"})
        assert result.success
        assert "Script Kiddie" in (game.last_event_message or "")
        repo.update.assert_awaited_once()

    async def test_upgrade_failure(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_upgrade = AsyncMock(return_value=(False, "Cannot upgrade", None))
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d._handle_upgrade(game, "p1", {"tile_id": "tile-1"})
        assert not result.success

    async def test_upgrade_success_missing_tile_skips_message(self) -> None:
        repo = make_mock_repo()
        economy_manager = MagicMock()
        economy_manager.handle_upgrade = AsyncMock(return_value=(True, "Upgraded!", "1337 Haxxor"))
        game = make_game(players=[], board=[])
        d = make_dispatcher(repo=repo, economy_manager=economy_manager)
        result = await d._handle_upgrade(game, "p1", {"tile_id": "nonexistent"})
        assert result.success
        repo.update.assert_awaited_once()


# ============================================================
# _handle_downgrade
# ============================================================


class TestHandleDowngrade:
    async def test_downgrade_success_level_0_logs_1337_haxxor(self) -> None:
        repo = make_mock_repo()
        economy_manager = MagicMock()
        economy_manager.handle_downgrade = AsyncMock(return_value=(True, "Downgraded!", 100))
        player = make_player("p1")
        tile = make_tile("tile-1", upgrade_level=0)  # after downgrade, level is 0
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher(repo=repo, economy_manager=economy_manager)
        result = await d._handle_downgrade(game, "p1", {"tile_id": "tile-1"})
        assert result.success
        assert "1337 HAXXOR" in (game.last_event_message or "")

    async def test_downgrade_success_level_1_logs_script_kiddie(self) -> None:
        repo = make_mock_repo()
        economy_manager = MagicMock()
        economy_manager.handle_downgrade = AsyncMock(return_value=(True, "Downgraded!", 50))
        player = make_player("p1")
        tile = make_tile("tile-1", upgrade_level=1)
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher(repo=repo, economy_manager=economy_manager)
        result = await d._handle_downgrade(game, "p1", {"tile_id": "tile-1"})
        assert result.success
        assert "SCRIPT KIDDIE" in (game.last_event_message or "")

    async def test_downgrade_failure(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_downgrade = AsyncMock(return_value=(False, "Cannot downgrade", 0))
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d._handle_downgrade(game, "p1", {"tile_id": "tile-1"})
        assert not result.success


# ============================================================
# _handle_buy_buff
# ============================================================


class TestHandleBuyBuff:
    def _market_game(self, player: Player, buffs: list[dict]) -> tuple[GameSession, MagicMock]:
        repo = make_mock_repo()
        game = make_game(
            turn_phase=TurnPhase.DECISION,
            players=[player],
            pending_decision=PendingDecision(
                type="MARKET",
                event_data={"buffs": buffs},
            ),
            event_deck=list(range(10)),
        )
        return game, repo

    async def test_not_in_market_returns_error(self) -> None:
        game = make_game(turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "VPN"})
        assert not result.success
        assert "Not in Market" in result.message

    async def test_invalid_buff_id(self) -> None:
        player = make_player("p1", cash=500)
        game, _ = self._market_game(player, [{"id": "VPN", "name": "VPN Shield", "cost": 100}])
        d = make_dispatcher()
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "NONEXISTENT"})
        assert not result.success
        assert "Invalid buff" in result.message

    async def test_player_not_found(self) -> None:
        game = make_game(
            turn_phase=TurnPhase.DECISION,
            players=[],
            pending_decision=PendingDecision(
                type="MARKET",
                event_data={"buffs": [{"id": "VPN", "name": "VPN Shield", "cost": 100}]},
            ),
        )
        d = make_dispatcher()
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "VPN"})
        assert not result.success
        assert "Player not found" in result.message

    async def test_already_has_buff(self) -> None:
        player = make_player("p1", cash=500, active_buff="VPN")
        game, _ = self._market_game(player, [{"id": "DDOS", "name": "DDoS Attack", "cost": 150}])
        d = make_dispatcher()
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "DDOS"})
        assert not result.success
        assert "already have an active buff" in result.message

    async def test_insufficient_funds(self) -> None:
        player = make_player("p1", cash=50)
        game, _ = self._market_game(player, [{"id": "VPN", "name": "VPN Shield", "cost": 100}])
        d = make_dispatcher()
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "VPN"})
        assert not result.success
        assert "Insufficient" in result.message

    async def test_buy_inventory_buff_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1", cash=500)
        game, _ = self._market_game(player, [{"id": "VPN", "name": "VPN Shield", "cost": 100}])
        game.players = [player]
        d = make_dispatcher(repo=repo)
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "VPN"})
        assert result.success
        assert player.active_buff == "VPN"
        assert player.cash == 400
        assert game.turn_phase == TurnPhase.POST_TURN
        repo.update_player_cash.assert_awaited()
        repo.update_player_buff.assert_awaited()

    async def test_buy_peek_buff_reveals_events(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1", cash=500)
        game, _ = self._market_game(player, [{"id": "PEEK", "name": "Insider Info", "cost": 100}])
        game.players = [player]
        game.event_deck = [0, 1, 2, 3, 4]
        turn_manager = MagicMock()
        turn_manager.ensure_deck_capacity = MagicMock()
        d = make_dispatcher(repo=repo, turn_manager=turn_manager)
        result = await d._handle_buy_buff(game, "p1", {"buff_id": "PEEK"})
        assert result.success
        assert player.active_buff is None  # PEEK is one-shot, no inventory buff
        assert player.cash == 400
        turn_manager.ensure_deck_capacity.assert_called_once()


# ============================================================
# _handle_block_tile
# ============================================================


class TestHandleBlockTile:
    async def test_not_your_turn(self) -> None:
        game = make_game(current_turn_player_id="p2")
        d = make_dispatcher()
        result = await d._handle_block_tile(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "Not your turn" in result.message

    async def test_wrong_phase(self) -> None:
        game = make_game(current_turn_player_id="p1", turn_phase=TurnPhase.POST_TURN)
        d = make_dispatcher()
        result = await d._handle_block_tile(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "PRE_ROLL" in result.message

    async def test_player_not_found(self) -> None:
        game = make_game(current_turn_player_id="p1", turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d._handle_block_tile(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "Player not found" in result.message

    async def test_no_ddos_buff(self) -> None:
        player = make_player("p1")
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.PRE_ROLL,
            players=[player],
        )
        d = make_dispatcher()
        result = await d._handle_block_tile(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "DDoS" in result.message

    async def test_invalid_tile(self) -> None:
        player = make_player("p1", active_buff="DDOS")
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.PRE_ROLL,
            players=[player],
            board=[],
        )
        d = make_dispatcher()
        result = await d._handle_block_tile(game, "p1", {"tile_id": "nonexistent"})
        assert not result.success
        assert "Invalid tile" in result.message

    async def test_block_tile_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1", active_buff="DDOS")
        tile = make_tile("tile-1")
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.PRE_ROLL,
            players=[player],
            board=[tile],
            current_round=3,
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_block_tile(game, "p1", {"tile_id": "tile-1"})
        assert result.success
        assert tile.blocked_until_round == 4
        assert player.active_buff is None
        repo.update_player_buff.assert_awaited()
        repo.save_board.assert_awaited()


# ============================================================
# _handle_propose_trade
# ============================================================


class TestHandleProposeTrade:
    async def test_not_your_turn(self) -> None:
        game = make_game(current_turn_player_id="p2")
        d = make_dispatcher()
        result = await d._handle_propose_trade(game, "p1", {"target_id": "p2"})
        assert not result.success
        assert "your turn" in result.message

    async def test_player_not_found(self) -> None:
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher()
        result = await d._handle_propose_trade(game, "p1", {"target_id": "p2"})
        assert not result.success
        assert "Player not found" in result.message

    async def test_trade_manager_error(self) -> None:
        player = make_player("p1")
        game = make_game(current_turn_player_id="p1", players=[player])
        trade_manager = MagicMock()
        trade_manager.create_trade_offer = MagicMock(return_value=(None, "Invalid trade"))
        d = make_dispatcher(trade_manager=trade_manager)
        result = await d._handle_propose_trade(game, "p1", {"target_id": "p2"})
        assert not result.success
        assert "Invalid trade" in result.message

    async def test_trade_created_successfully(self) -> None:
        repo = make_mock_repo()
        player1 = make_player("p1")
        player2 = make_player("p2", name="Bob")
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=100,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(
            current_turn_player_id="p1",
            players=[player1, player2],
        )
        trade_manager = MagicMock()
        trade_manager.create_trade_offer = MagicMock(return_value=(offer, None))
        d = make_dispatcher(repo=repo, trade_manager=trade_manager)
        result = await d._handle_propose_trade(game, "p1", {"target_id": "p2"})
        assert result.success
        assert offer in game.active_trade_offers
        repo.update.assert_awaited_once()


# ============================================================
# _handle_accept_trade
# ============================================================


class TestHandleAcceptTrade:
    def _make_trade_game(self) -> tuple[GameSession, TradeOffer, Player, Player, MagicMock]:
        repo = make_mock_repo()
        initiator = make_player("p1", cash=500, properties=["tile-1"])
        target = make_player("p2", cash=500, properties=["tile-2"])
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=100,
            offering_properties=["tile-1"],
            requesting_cash=50,
            requesting_properties=["tile-2"],
        )
        tile1 = make_tile("tile-1", owner_id="p1")
        tile2 = make_tile("tile-2", owner_id="p2")
        game = make_game(
            players=[initiator, target],
            board=[tile1, tile2],
            active_trade_offers=[offer],
        )
        return game, offer, initiator, target, repo

    async def test_trade_not_found(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_accept_trade(game, "p2", {"trade_id": "no-such-id"})
        assert not result.success
        assert "not found" in result.message

    async def test_not_authorized_to_accept(self) -> None:
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(active_trade_offers=[offer])
        d = make_dispatcher()
        result = await d._handle_accept_trade(game, "p1", {"trade_id": "offer-1"})
        assert not result.success
        assert "Not authorized" in result.message

    async def test_initiator_gone(self) -> None:
        repo = make_mock_repo()
        target = make_player("p2")
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",  # p1 not in players
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(players=[target], active_trade_offers=[offer])
        d = make_dispatcher(repo=repo)
        result = await d._handle_accept_trade(game, "p2", {"trade_id": "offer-1"})
        assert not result.success
        assert "Initiator gone" in result.message

    async def test_trade_validation_error(self) -> None:
        game, offer, initiator, target, repo = self._make_trade_game()
        trade_manager = MagicMock()
        trade_manager.validate_trade_assets = MagicMock(return_value="Cannot trade upgraded")
        d = make_dispatcher(repo=repo, trade_manager=trade_manager)
        result = await d._handle_accept_trade(game, "p2", {"trade_id": "offer-1"})
        assert not result.success
        assert "Cannot trade upgraded" in result.message

    async def test_trade_executed_successfully(self) -> None:
        game, offer, initiator, target, repo = self._make_trade_game()
        trade_manager = MagicMock()
        trade_manager.validate_trade_assets = MagicMock(return_value=None)
        trade_manager.execute_trade_transfer = MagicMock(
            return_value={
                "initiator_cash": 450,
                "target_cash": 550,
                "property_transfers": {
                    "initiator_to_target": ["tile-1"],
                    "target_to_initiator": ["tile-2"],
                },
            }
        )
        d = make_dispatcher(repo=repo, trade_manager=trade_manager)
        result = await d._handle_accept_trade(game, "p2", {"trade_id": "offer-1"})
        assert result.success
        assert "Trade completed" in result.message
        assert initiator.cash == 450
        assert target.cash == 550
        assert offer not in game.active_trade_offers


# ============================================================
# _handle_decline_trade
# ============================================================


class TestHandleDeclineTrade:
    async def test_trade_not_found(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_decline_trade(game, "p2", {"trade_id": "no-such"})
        assert not result.success
        assert "not found" in result.message.lower()

    async def test_not_authorized(self) -> None:
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(active_trade_offers=[offer])
        d = make_dispatcher()
        result = await d._handle_decline_trade(game, "p1", {"trade_id": "offer-1"})
        assert not result.success

    async def test_decline_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p2")
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(players=[player], active_trade_offers=[offer])
        d = make_dispatcher(repo=repo)
        result = await d._handle_decline_trade(game, "p2", {"trade_id": "offer-1"})
        assert result.success
        assert offer not in game.active_trade_offers
        repo.update.assert_awaited_once()


# ============================================================
# _handle_cancel_trade
# ============================================================


class TestHandleCancelTrade:
    async def test_trade_not_found(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_cancel_trade(game, "p1", {"trade_id": "no-such"})
        assert not result.success

    async def test_not_authorized_initiator(self) -> None:
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(active_trade_offers=[offer])
        d = make_dispatcher()
        result = await d._handle_cancel_trade(game, "p2", {"trade_id": "offer-1"})
        assert not result.success

    async def test_cancel_success(self) -> None:
        repo = make_mock_repo()
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(active_trade_offers=[offer])
        d = make_dispatcher(repo=repo)
        result = await d._handle_cancel_trade(game, "p1", {"trade_id": "offer-1"})
        assert result.success
        assert offer not in game.active_trade_offers
        repo.update.assert_awaited_once()


# ============================================================
# _resolve_auction
# ============================================================


class TestResolveAuction:
    async def test_resolve_fails(self) -> None:
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(
            return_value=(False, "Not ended", None, 0, None)
        )
        game = make_game()
        d = make_dispatcher(auction_manager=auction_manager)
        result = await d._resolve_auction(game)
        assert not result.success

    async def test_resolve_no_winner(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(return_value=(True, "No bids", None, 0, None))
        game = make_game()
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._resolve_auction(game)
        assert result.success

    async def test_resolve_with_winner_updates_player(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(
            return_value=(True, "Sold!", "p1", 150, "tile-1")
        )
        player = make_player("p1", cash=500)
        tile = make_tile("tile-1")
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._resolve_auction(game)
        assert result.success
        assert player.cash == 350
        assert "tile-1" in player.properties
        assert tile.owner_id == "p1"
        repo.update_player_cash.assert_awaited()
        repo.update_player_properties.assert_awaited()
        repo.update_tile_owner.assert_awaited()

    async def test_resolve_advances_bankruptcy_auction_queue(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(
            return_value=(True, "Sold bankrupt prop!", "p1", 50, "tile-1")
        )
        auction_manager.start_auction = MagicMock()
        player = make_player("p1", cash=500)
        tile1 = make_tile("tile-1")
        tile2 = make_tile("tile-2")
        game = make_game(
            players=[player],
            board=[tile1, tile2],
            bankruptcy_auction_queue=["tile-1", "tile-2"],
        )
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d._resolve_auction(game)
        assert result.success
        assert game.bankruptcy_auction_queue == ["tile-2"]
        auction_manager.start_auction.assert_called_once()

    async def test_resolve_clears_empty_bankruptcy_queue(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(
            return_value=(True, "Last prop sold!", "p1", 50, "tile-1")
        )
        player = make_player("p1", cash=500)
        tile = make_tile("tile-1")
        game = make_game(
            players=[player],
            board=[tile],
            bankruptcy_auction_queue=["tile-1"],
        )
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        await d._resolve_auction(game)
        assert game.bankruptcy_auction_queue == []


# ============================================================
# _handle_buy_release (jail)
# ============================================================


class TestHandleBuyRelease:
    async def test_no_jail_manager(self) -> None:
        game = make_game()
        d = make_dispatcher(jail_manager=None)
        result = await d._handle_buy_release(game, "p1")
        assert not result.success
        assert "Jail manager" in result.message

    async def test_player_not_found(self) -> None:
        jail_manager = MagicMock()
        game = make_game(players=[])
        d = make_dispatcher(jail_manager=jail_manager)
        result = await d._handle_buy_release(game, "p1")
        assert not result.success
        assert "Player not found" in result.message

    async def test_release_success(self) -> None:
        repo = make_mock_repo()
        jail_manager = MagicMock()
        jail_manager.attempt_bribe_release = MagicMock(return_value=(True, "Paid $50 bribe!"))
        player = make_player("p1", cash=200, in_jail=True)
        game = make_game(players=[player])
        d = make_dispatcher(repo=repo, jail_manager=jail_manager)
        result = await d._handle_buy_release(game, "p1")
        assert result.success
        repo.update_player_cash.assert_awaited()
        repo.update_player_jail.assert_awaited()

    async def test_release_failure(self) -> None:
        jail_manager = MagicMock()
        jail_manager.attempt_bribe_release = MagicMock(return_value=(False, "Not enough cash"))
        player = make_player("p1", cash=10, in_jail=True)
        game = make_game(players=[player])
        d = make_dispatcher(jail_manager=jail_manager)
        result = await d._handle_buy_release(game, "p1")
        assert not result.success


# ============================================================
# _handle_roll_for_doubles (jail)
# ============================================================


class TestHandleRollForDoubles:
    async def test_no_jail_manager(self) -> None:
        game = make_game()
        d = make_dispatcher(jail_manager=None)
        result = await d._handle_roll_for_doubles(game, "p1")
        assert not result.success

    async def test_player_not_found(self) -> None:
        jail_manager = MagicMock()
        game = make_game(players=[])
        d = make_dispatcher(jail_manager=jail_manager)
        result = await d._handle_roll_for_doubles(game, "p1")
        assert not result.success

    async def test_escaped(self) -> None:
        repo = make_mock_repo()
        jail_manager = MagicMock()
        jail_manager.roll_for_doubles = MagicMock(return_value=(True, 3, 3, "Rolled doubles!"))
        player = make_player("p1", in_jail=True)
        game = make_game(players=[player])
        d = make_dispatcher(repo=repo, jail_manager=jail_manager)
        result = await d._handle_roll_for_doubles(game, "p1")
        assert result.success
        assert result.data["escaped"] is True  # type: ignore[index]
        assert result.data["dice1"] == 3  # type: ignore[index]

    async def test_still_jailed(self) -> None:
        repo = make_mock_repo()
        jail_manager = MagicMock()
        jail_manager.roll_for_doubles = MagicMock(return_value=(False, 2, 4, "No doubles"))
        player = make_player("p1", in_jail=True)
        game = make_game(players=[player])
        d = make_dispatcher(repo=repo, jail_manager=jail_manager)
        result = await d._handle_roll_for_doubles(game, "p1")
        assert not result.success
        assert result.data["escaped"] is False  # type: ignore[index]


# ============================================================
# _handle_event_clone_upgrade
# ============================================================


class TestHandleEventCloneUpgrade:
    async def test_missing_tiles(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(game, "p1", {})
        assert not result.success
        assert "source and target" in result.message

    async def test_player_not_found(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert not result.success

    async def test_tiles_not_found(self) -> None:
        player = make_player("p1")
        game = make_game(players=[player], board=[])
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert not result.success
        assert "Tile not found" in result.message

    async def test_source_has_no_upgrades(self) -> None:
        player = make_player("p1")
        source = make_tile("s", upgrade_level=0)
        target = make_tile("t", owner_id="p1")
        game = make_game(players=[player], board=[source, target])
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert not result.success
        assert "no upgrades" in result.message

    async def test_target_not_owned(self) -> None:
        player = make_player("p1")
        source = make_tile("s", upgrade_level=1, owner_id="p2")
        target = make_tile("t", owner_id="p2")
        game = make_game(players=[player], board=[source, target])
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert not result.success

    async def test_target_not_property_type(self) -> None:
        player = make_player("p1")
        source = make_tile("s", upgrade_level=1)
        target = make_tile("t", tile_type=TileType.TAX, owner_id="p1")
        game = make_game(players=[player], board=[source, target])
        d = make_dispatcher()
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert not result.success
        assert "properties" in result.message

    async def test_clone_upgrade_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1")
        source = make_tile("s", upgrade_level=2)
        target = make_tile("t", owner_id="p1", upgrade_level=0)
        game = make_game(
            players=[player],
            board=[source, target],
            turn_phase=TurnPhase.DECISION,
            pending_decision=PendingDecision(type="EVENT"),
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_event_clone_upgrade(
            game, "p1", {"source_tile_id": "s", "target_tile_id": "t"}
        )
        assert result.success
        assert target.upgrade_level == 2
        assert game.turn_phase == TurnPhase.POST_TURN
        repo.save_board.assert_awaited()


# ============================================================
# _handle_event_force_buy
# ============================================================


class TestHandleEventForceBuy:
    async def test_missing_tile_id(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_event_force_buy(game, "p1", {})
        assert not result.success

    async def test_player_not_found(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d._handle_event_force_buy(game, "p1", {"tile_id": "tile-1"})
        assert not result.success

    async def test_tile_not_found(self) -> None:
        player = make_player("p1")
        game = make_game(players=[player], board=[])
        d = make_dispatcher()
        result = await d._handle_event_force_buy(game, "p1", {"tile_id": "tile-1"})
        assert not result.success

    async def test_property_not_owned_by_other(self) -> None:
        player = make_player("p1")
        tile = make_tile("tile-1", owner_id=None)
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher()
        result = await d._handle_event_force_buy(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "owned by another player" in result.message

    async def test_insufficient_funds(self) -> None:
        player = make_player("p1", cash=10)
        tile = make_tile("tile-1", price=200, owner_id="p2")
        owner = make_player("p2", cash=500)
        game = make_game(players=[player, owner], board=[tile])
        d = make_dispatcher()
        result = await d._handle_event_force_buy(game, "p1", {"tile_id": "tile-1"})
        assert not result.success
        assert "Insufficient" in result.message

    async def test_force_buy_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1", cash=500, properties=[])
        owner = make_player("p2", cash=200, properties=["tile-1"])
        tile = make_tile("tile-1", price=200, owner_id="p2")
        # cost = int(200 * 1.5) = 300
        game = make_game(
            players=[player, owner],
            board=[tile],
            pending_decision=PendingDecision(type="EVENT"),
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_event_force_buy(game, "p1", {"tile_id": "tile-1"})
        assert result.success
        assert player.cash == 200  # 500 - 300
        assert owner.cash == 500  # 200 + 300
        assert "tile-1" in player.properties
        assert "tile-1" not in owner.properties
        assert tile.owner_id == "p1"
        assert game.turn_phase == TurnPhase.POST_TURN


# ============================================================
# _handle_event_free_landing
# ============================================================


class TestHandleEventFreeLanding:
    async def test_missing_tile_id(self) -> None:
        game = make_game()
        d = make_dispatcher()
        result = await d._handle_event_free_landing(game, "p1", {})
        assert not result.success

    async def test_player_not_found(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d._handle_event_free_landing(game, "p1", {"tile_id": "t"})
        assert not result.success

    async def test_tile_not_found(self) -> None:
        player = make_player("p1")
        game = make_game(players=[player], board=[])
        d = make_dispatcher()
        result = await d._handle_event_free_landing(game, "p1", {"tile_id": "t"})
        assert not result.success

    async def test_tile_not_owned_by_player(self) -> None:
        player = make_player("p1")
        tile = make_tile("t", owner_id="p2")
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher()
        result = await d._handle_event_free_landing(game, "p1", {"tile_id": "t"})
        assert not result.success
        assert "own the property" in result.message

    async def test_free_landing_success(self) -> None:
        repo = make_mock_repo()
        player = make_player("p1")
        tile = make_tile("t", owner_id="p1")
        game = make_game(
            players=[player],
            board=[tile],
            current_round=2,
            pending_decision=PendingDecision(
                type="EVENT",
                event_data={"actions": {"free_rounds": 2}},
            ),
        )
        d = make_dispatcher(repo=repo)
        result = await d._handle_event_free_landing(game, "p1", {"tile_id": "t"})
        assert result.success
        assert tile.free_landing_until_round == 4  # 2 + 2
        assert game.turn_phase == TurnPhase.POST_TURN
        repo.save_board.assert_awaited()


# ============================================================
# _check_and_handle_end_conditions
# ============================================================


class TestCheckAndHandleEndConditions:
    async def test_no_game_raises_value_error(self) -> None:
        repo = make_mock_repo()
        repo.get_by_id = AsyncMock(return_value=None)
        d = make_dispatcher(repo=repo)
        with pytest.raises(ValueError, match="not found"):
            await d._check_and_handle_end_conditions("nonexistent")

    async def test_bankrupt_player_gets_flagged(self) -> None:
        repo = make_mock_repo()
        player1 = make_player("p1", cash=-100)
        player2 = make_player("p2", cash=500)
        game = make_game(players=[player1, player2])
        repo.get_by_id = AsyncMock(return_value=game)
        d = make_dispatcher(repo=repo)
        await d._check_and_handle_end_conditions("game-1")
        assert player1.is_bankrupt is True
        repo.update_player_bankrupt.assert_awaited()

    async def test_first_to_cash_win_condition(self) -> None:
        from app.modules.sastadice.schemas import WinCondition

        repo = make_mock_repo()
        settings = make_settings(win_condition=WinCondition.FIRST_TO_CASH, target_cash=500)
        player1 = make_player("p1", cash=600)
        player2 = make_player("p2", cash=200)
        game = make_game(players=[player1, player2], settings=settings)
        # repo.get_by_id returns the game each time (called twice in FIRST_TO_CASH branch)
        repo.get_by_id = AsyncMock(return_value=game)
        d = make_dispatcher(repo=repo)
        ended = await d._check_and_handle_end_conditions("game-1")
        assert ended is True
        assert game.winner_id == "p1"

    async def test_last_standing_one_player_left(self) -> None:
        repo = make_mock_repo()
        player1 = make_player("p1", cash=500)
        player2 = make_player("p2", cash=100, is_bankrupt=True)
        game = make_game(players=[player1, player2])
        repo.get_by_id = AsyncMock(return_value=game)
        d = make_dispatcher(repo=repo)
        ended = await d._check_and_handle_end_conditions("game-1")
        assert ended is True
        assert game.winner_id == "p1"

    async def test_all_bankrupt_picks_richest(self) -> None:
        repo = make_mock_repo()
        player1 = make_player("p1", cash=10, is_bankrupt=True)
        player2 = make_player("p2", cash=50, is_bankrupt=True)
        game = make_game(players=[player1, player2])
        repo.get_by_id = AsyncMock(return_value=game)
        d = make_dispatcher(repo=repo)
        ended = await d._check_and_handle_end_conditions("game-1")
        assert ended is True
        assert game.winner_id == "p2"  # max cash

    async def test_game_continues_when_multiple_active(self) -> None:
        from app.modules.sastadice.schemas import WinCondition

        repo = make_mock_repo()
        settings = make_settings(win_condition=WinCondition.SUDDEN_DEATH, target_cash=10000)
        player1 = make_player("p1", cash=200)
        player2 = make_player("p2", cash=300)
        game = make_game(players=[player1, player2], settings=settings)
        repo.get_by_id = AsyncMock(return_value=game)
        d = make_dispatcher(repo=repo)
        ended = await d._check_and_handle_end_conditions("game-1")
        assert ended is False


# ============================================================
# _handle_end_turn (delegates to turn_coordinator)
# ============================================================


class TestHandleEndTurn:
    async def test_end_turn_delegates_to_coordinator(self) -> None:
        turn_coordinator = MagicMock()
        turn_coordinator.handle_end_turn = AsyncMock(
            return_value=ActionResult(success=True, message="Turn ended")
        )
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher(turn_coordinator=turn_coordinator)
        result = await d._handle_end_turn(game, "p1")
        assert result.success
        turn_coordinator.handle_end_turn.assert_awaited_once()


# ============================================================
# _handle_roll_dice
# ============================================================


class TestHandleRollDice:
    async def test_uses_callback_if_provided(self) -> None:
        repo = make_mock_repo()
        from app.modules.sastadice.schemas import DiceRollResult

        dice_result = DiceRollResult(dice1=3, dice2=4, total=7, is_doubles=False)
        roll_callback = AsyncMock(return_value=dice_result)

        player = make_player("p1", position=7)
        updated_game = make_game(
            id="game-1",
            players=[player],
            turn_phase=TurnPhase.DECISION,
        )
        repo.get_by_id = AsyncMock(return_value=updated_game)

        game = make_game(id="game-1", players=[player])
        d = make_dispatcher(repo=repo, roll_dice_callback=roll_callback)
        result = await d._handle_roll_dice(game, "p1")
        assert result.success
        roll_callback.assert_awaited_once_with("game-1", "p1")

    async def test_handles_value_error(self) -> None:
        turn_coordinator = MagicMock()
        turn_coordinator.roll_dice = AsyncMock(side_effect=ValueError("Not your turn"))
        game = make_game()
        d = make_dispatcher(turn_coordinator=turn_coordinator)
        result = await d._handle_roll_dice(game, "p1")
        assert not result.success
        assert "Not your turn" in result.message


# ============================================================
# _determine_winner / _determine_winner_async
# ============================================================


class TestDetermineWinner:
    async def test_determine_winner_async_delegates(self) -> None:
        economy_manager = MagicMock()
        economy_manager.determine_winner = MagicMock(return_value={"winner_id": "p1"})
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d._determine_winner_async(game)
        assert result == {"winner_id": "p1"}
        economy_manager.determine_winner.assert_called_once_with(game)

    def test_determine_winner_sync(self) -> None:
        economy_manager = MagicMock()
        economy_manager.determine_winner = MagicMock(return_value=None)
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = d._determine_winner(game)
        assert result is None


# ============================================================
# dispatch() routing — covers the match-case lines
# ============================================================


class TestDispatchRouting:
    """Each test exercises a different dispatch branch to hit the case-arm lines."""

    async def test_dispatch_buy_property(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_buy_property = AsyncMock(
            return_value=(False, "Cannot buy now", None, None)
        )
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d.dispatch(game, "p1", ActionType.BUY_PROPERTY, {})
        assert isinstance(result, ActionResult)

    async def test_dispatch_pass_property(self) -> None:
        repo = make_mock_repo()
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.DECISION,
            pending_decision=PendingDecision(type="BUY", tile_id=None),
        )
        d = make_dispatcher(repo=repo)
        result = await d.dispatch(game, "p1", ActionType.PASS_PROPERTY, {})
        assert isinstance(result, ActionResult)

    async def test_dispatch_bid_valid_payload(self) -> None:
        auction = AuctionState(
            property_id="tile-1",
            highest_bid=0,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=["p1"],
        )
        game = make_game(turn_phase=TurnPhase.AUCTION, auction_state=auction)
        auction_manager = MagicMock()
        auction_manager.check_auction_timeout = MagicMock(return_value=False)
        auction_manager.place_bid = MagicMock(return_value=(True, "Bid placed"))
        repo = make_mock_repo()
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d.dispatch(game, "p1", ActionType.BID, {"amount": 50})
        assert isinstance(result, ActionResult)

    async def test_dispatch_resolve_auction(self) -> None:
        repo = make_mock_repo()
        auction_manager = MagicMock()
        auction_manager.resolve_auction = MagicMock(return_value=(True, "Done", None, 0, None))
        game = make_game()
        d = make_dispatcher(repo=repo, auction_manager=auction_manager)
        result = await d.dispatch(game, "p1", ActionType.RESOLVE_AUCTION, {})
        assert isinstance(result, ActionResult)

    async def test_dispatch_upgrade(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_upgrade = AsyncMock(return_value=(False, "Cannot upgrade", None))
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d.dispatch(game, "p1", ActionType.UPGRADE, {"tile_id": "t-1"})
        assert isinstance(result, ActionResult)

    async def test_dispatch_downgrade(self) -> None:
        economy_manager = MagicMock()
        economy_manager.handle_downgrade = AsyncMock(return_value=(False, "Cannot downgrade", 0))
        game = make_game()
        d = make_dispatcher(economy_manager=economy_manager)
        result = await d.dispatch(game, "p1", ActionType.DOWNGRADE, {"tile_id": "t-1"})
        assert isinstance(result, ActionResult)

    async def test_dispatch_buy_buff(self) -> None:
        game = make_game(turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.BUY_BUFF, {"buff_id": "VPN"})
        assert not result.success  # Not in Market

    async def test_dispatch_block_tile(self) -> None:
        game = make_game(current_turn_player_id="p2", turn_phase=TurnPhase.PRE_ROLL)
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.BLOCK_TILE, {"tile_id": "t-1"})
        assert not result.success

    async def test_dispatch_propose_trade(self) -> None:
        game = make_game(current_turn_player_id="p2")
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.PROPOSE_TRADE, {"target_id": "p2"})
        assert not result.success

    async def test_dispatch_accept_trade(self) -> None:
        game = make_game(active_trade_offers=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p2", ActionType.ACCEPT_TRADE, {"trade_id": "no-such"})
        assert not result.success

    async def test_dispatch_decline_trade(self) -> None:
        game = make_game(active_trade_offers=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p2", ActionType.DECLINE_TRADE, {"trade_id": "no-such"})
        assert not result.success

    async def test_dispatch_cancel_trade(self) -> None:
        game = make_game(active_trade_offers=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.CANCEL_TRADE, {"trade_id": "no-such"})
        assert not result.success

    async def test_dispatch_end_turn(self) -> None:
        turn_coordinator = MagicMock()
        turn_coordinator.handle_end_turn = AsyncMock(
            return_value=ActionResult(success=True, message="OK")
        )
        game = make_game(current_turn_player_id="p1")
        d = make_dispatcher(turn_coordinator=turn_coordinator)
        result = await d.dispatch(game, "p1", ActionType.END_TURN, {})
        assert result.success

    async def test_dispatch_buy_release(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher(jail_manager=MagicMock())
        result = await d.dispatch(game, "p1", ActionType.BUY_RELEASE, {})
        assert not result.success

    async def test_dispatch_roll_for_doubles(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher(jail_manager=MagicMock())
        result = await d.dispatch(game, "p1", ActionType.ROLL_FOR_DOUBLES, {})
        assert not result.success

    async def test_dispatch_event_clone_upgrade(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.EVENT_CLONE_UPGRADE, {})
        assert not result.success

    async def test_dispatch_event_force_buy(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.EVENT_FORCE_BUY, {})
        assert not result.success

    async def test_dispatch_event_free_landing(self) -> None:
        game = make_game(players=[])
        d = make_dispatcher()
        result = await d.dispatch(game, "p1", ActionType.EVENT_FREE_LANDING, {})
        assert not result.success

    async def test_dispatch_roll_dice_no_callback(self) -> None:
        """Covers _handle_roll_dice when no callback and TurnCoordinator raises."""
        turn_coordinator = MagicMock()
        turn_coordinator.roll_dice = AsyncMock(side_effect=ValueError("Phase error"))
        game = make_game()
        d = make_dispatcher(turn_coordinator=turn_coordinator)
        result = await d.dispatch(game, "p1", ActionType.ROLL_DICE, {})
        assert not result.success

    async def test_send_to_jail_callback_with_jail_manager(self) -> None:
        """Covers _send_to_jail_callback when jail_manager is available."""
        repo = make_mock_repo()
        jail_manager = MagicMock()
        jail_manager.send_to_jail = MagicMock()
        player = make_player("p1")
        tile = make_tile("t1")
        game = make_game(players=[player], board=[tile] * 20)
        d = make_dispatcher(repo=repo, jail_manager=jail_manager)
        # call directly
        await d._send_to_jail_callback(game, player)
        jail_manager.send_to_jail.assert_called_once_with(game, player)
        repo.update_player_position.assert_awaited_once()

    async def test_send_to_jail_callback_without_jail_manager(self) -> None:
        """Covers _send_to_jail_callback when jail_manager is None (no-op)."""
        player = make_player("p1")
        game = make_game(players=[player], board=[])
        d = make_dispatcher(jail_manager=None)
        # Should not raise, just be a no-op
        await d._send_to_jail_callback(game, player)

    async def test_handle_tile_landing_callback_is_noop(self) -> None:
        """Covers _handle_tile_landing_callback (pass)."""
        player = make_player("p1")
        tile = make_tile("t1")
        game = make_game(players=[player], board=[tile])
        d = make_dispatcher()
        result = await d._handle_tile_landing_callback(game, player, tile)
        assert result is None

    async def test_block_tile_missing_tile_id_in_payload(self) -> None:
        """Covers line 362: BLOCK_TILE payload has no tile_id value."""
        player = make_player("p1", active_buff="DDOS")
        game = make_game(
            current_turn_player_id="p1",
            turn_phase=TurnPhase.PRE_ROLL,
            players=[player],
        )
        d = make_dispatcher()
        # tile_id key is absent from payload entirely
        result = await d._handle_block_tile(game, "p1", {})
        assert not result.success
        assert "Target tile required" in result.message

    async def test_propose_trade_no_offer_and_no_error(self) -> None:
        """Covers line 401: trade_manager returns (None, None) — offer is falsy."""
        repo = make_mock_repo()
        player = make_player("p1")
        game = make_game(current_turn_player_id="p1", players=[player])
        trade_manager = MagicMock()
        trade_manager.create_trade_offer = MagicMock(return_value=(None, None))
        d = make_dispatcher(repo=repo, trade_manager=trade_manager)
        result = await d._handle_propose_trade(game, "p1", {"target_id": "p2"})
        assert not result.success
        assert "Failed to create trade offer" in result.message

    async def test_accept_trade_target_player_not_in_game(self) -> None:
        """Covers lines 423-425: target player is not in game.players list."""
        repo = make_mock_repo()
        initiator = make_player("p1")
        # Note: "p2" is NOT in game.players
        offer = TradeOffer(
            id="offer-1",
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
        )
        game = make_game(players=[initiator], active_trade_offers=[offer])
        d = make_dispatcher(repo=repo)
        result = await d._handle_accept_trade(game, "p2", {"trade_id": "offer-1"})
        assert not result.success
        assert "Player not found" in result.message
