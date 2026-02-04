"""Turn manager for pure game rules - no database access."""

import random
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player, Tile

from app.modules.sastadice.events.event_manager import EventManager
from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import PendingDecision, TileType, TurnPhase


class TurnManager:
    """Pure game rules engine - mutates GameSession but makes no DB calls."""

    @staticmethod
    def calculate_go_bonus(game: "GameSession") -> int:
        """Calculate GO bonus with inflation using game settings."""
        base = game.settings.go_bonus_base
        inflation = game.current_round * game.settings.go_inflation_per_round
        multiplier = getattr(game, "go_bonus_multiplier", 1.0)
        return int((base + inflation) * multiplier)

    @staticmethod
    def owns_full_set(player: "Player", color: str, board: list["Tile"]) -> bool:
        """Check if player owns all properties of a color."""
        if not color:
            return False
        color_tiles = [t for t in board if t.type == TileType.PROPERTY and t.color == color]
        if not color_tiles:
            return False
        return all(t.owner_id == player.id for t in color_tiles)

    @staticmethod
    def calculate_rent(tile: "Tile", owner: "Player", game: "GameSession") -> int:
        """Calculate rent with set bonus and upgrades."""
        if tile.type != TileType.PROPERTY:
            return 0

        base_rent = tile.rent

        if tile.color and TurnManager.owns_full_set(owner, tile.color, game.board):
            base_rent *= 2

        if tile.upgrade_level == 1:
            base_rent = int(base_rent * 1.5)
        elif tile.upgrade_level == 2:
            base_rent = int(base_rent * 3.0)

        base_rent = int(base_rent * game.rent_multiplier)

        if tile.blocked_until_round and tile.blocked_until_round > game.current_round:
            return 0

        if tile.id in game.blocked_tiles:
            return 0

        return base_rent

    @staticmethod
    def initialize_event_deck(game: "GameSession") -> None:
        """Initialize and shuffle the event deck (delegates to EventManager)."""
        EventManager.initialize_deck(game)

    @staticmethod
    def ensure_deck_capacity(game: "GameSession", count: int = 3) -> None:
        """Ensure deck has enough cards by reshuffling discard if needed."""
        EventManager.ensure_capacity(game, count)

    @staticmethod
    def draw_event(game: "GameSession") -> dict[str, Any] | None:
        """Draw next event from deck (delegates to EventManager)."""
        return EventManager.draw_event(game)

    @staticmethod
    def handle_go_landing(game: "GameSession", tile: "Tile") -> None:
        """Handle landing on GO tile."""
        go_bonus = TurnManager.calculate_go_bonus(game)
        game.last_event_message = f"Welcome to GO! Collect ${go_bonus} when you pass."
        game.turn_phase = TurnPhase.POST_TURN

    @staticmethod
    def handle_property_landing(
        game: "GameSession", player: "Player", tile: "Tile"
    ) -> dict[str, Any]:
        """Handle landing on property tile - returns action dict for orchestrator."""
        if tile.owner_id is None:
            game.pending_decision = PendingDecision(type="BUY", tile_id=tile.id, price=tile.price)
            color_info = f" [{tile.color}]" if tile.color else ""
            game.last_event_message = f"'{tile.name}'{color_info} is for sale! Price: ${tile.price}"
            return {"action": "buy_decision", "tile_id": tile.id}
        elif tile.owner_id == player.id:
            game.last_event_message = f"You own '{tile.name}'. Safe!"
            game.turn_phase = TurnPhase.POST_TURN
            return {"action": "owned_by_player"}
        else:
            return {"action": "pay_rent", "tile_id": tile.id, "owner_id": tile.owner_id}

    @staticmethod
    def handle_chance_landing(
        game: "GameSession", player: "Player", tile: "Tile"
    ) -> dict[str, Any]:
        """Handle landing on chance tile - returns event dict for orchestrator to apply."""
        event = TurnManager.draw_event(game)
        if not event:
            event = random.choice(SASTA_EVENTS)
        return event

    @staticmethod
    def handle_tax_landing(game: "GameSession", player: "Player", tile: "Tile") -> int:
        """Handle landing on tax tile - returns amount to charge."""
        go_bonus = TurnManager.calculate_go_bonus(game)
        tax_amount = tile.price if tile.price > 0 else go_bonus // 2
        game.turn_phase = TurnPhase.POST_TURN
        return tax_amount

    @staticmethod
    def handle_buff_landing(game: "GameSession", player: "Player", tile: "Tile") -> int:
        """Handle landing on buff tile - returns amount to give."""
        go_bonus = TurnManager.calculate_go_bonus(game)
        buff_amount = go_bonus // 2
        game.turn_phase = TurnPhase.POST_TURN
        return buff_amount

    @staticmethod
    def handle_trap_landing(game: "GameSession", player: "Player", tile: "Tile") -> int:
        """Handle landing on trap tile - returns amount to charge."""
        go_bonus = TurnManager.calculate_go_bonus(game)
        trap_amount = go_bonus // 3
        game.turn_phase = TurnPhase.POST_TURN
        return trap_amount

    @staticmethod
    def handle_market_landing(game: "GameSession") -> None:
        """Handle landing on market tile."""
        game.pending_decision = PendingDecision(
            type="MARKET",
            event_data={
                "buffs": [
                    {
                        "id": "VPN",
                        "name": "VPN (Immunity)",
                        "cost": 200,
                        "desc": "Block next rent",
                    },
                    {
                        "id": "DDOS",
                        "name": "DDoS (Blockade)",
                        "cost": 150,
                        "desc": "Disable a tile",
                    },
                    {
                        "id": "PEEK",
                        "name": "Insider Info",
                        "cost": 100,
                        "desc": "See next 3 events",
                    },
                ]
            },
        )
        game.last_event_message = "🛒 Welcome to the BLACK MARKET! Buy a buff."

    @staticmethod
    def handle_jail_landing(game: "GameSession") -> None:
        """Handle landing on jail tile (just visiting)."""
        game.last_event_message = "👀 Just visiting SERVER DOWNTIME. Stay safe!"
        game.turn_phase = TurnPhase.POST_TURN

    @staticmethod
    def handle_glitch_teleport(game: "GameSession", player: "Player") -> Optional["Tile"]:
        """Handle glitch teleport - returns target tile for orchestrator to move to."""
        unowned = [t for t in game.board if t.type == TileType.PROPERTY and not t.owner_id]

        if unowned:
            target = random.choice(unowned)
        else:
            events = [t for t in game.board if t.type == TileType.CHANCE]
            target = random.choice(events) if events else game.board[0]

        return target

    @staticmethod
    def resolve_tile_landing(game: "GameSession", player: "Player", tile: "Tile") -> dict[str, Any]:
        """Resolve tile landing - returns action dict for orchestrator."""
        handler_map: dict[TileType, Any] = {
            TileType.GO: lambda: TurnManager.handle_go_landing(game, tile),
            TileType.PROPERTY: lambda: TurnManager.handle_property_landing(game, player, tile),
            TileType.CHANCE: lambda: TurnManager.handle_chance_landing(game, player, tile),
            TileType.TAX: lambda: TurnManager.handle_tax_landing(game, player, tile),
            TileType.BUFF: lambda: TurnManager.handle_buff_landing(game, player, tile),
            TileType.TRAP: lambda: TurnManager.handle_trap_landing(game, player, tile),
            TileType.JAIL: lambda: TurnManager.handle_jail_landing(game),
            TileType.TELEPORT: lambda: TurnManager.handle_glitch_teleport(game, player),
            TileType.MARKET: lambda: TurnManager.handle_market_landing(game),
        }

        handler = handler_map.get(tile.type)
        if handler:
            result = handler()
            return {"type": tile.type.value, "result": result}
        else:
            game.last_event_message = f"Landed on '{tile.name}'. Nothing happens."
            game.turn_phase = TurnPhase.POST_TURN
            return {"type": "NEUTRAL", "result": None}

    @staticmethod
    def apply_event_effect(
        game: "GameSession", player: "Player", event: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply event effect - returns action dict for orchestrator.
        NOTE: This is a legacy method. For new code, use EventManager.apply_effect
        which includes repository updates. This method only returns action dicts.
        """
        actions: dict[str, Any] = {
            "cash_changes": {},
            "position_changes": {},
            "skip_buy": False,
            "special": None,
        }

        if event["type"] == "CASH_GAIN":
            actions["cash_changes"][player.id] = event["value"]

        elif event["type"] == "CASH_LOSS":
            actions["cash_changes"][player.id] = -event["value"]

        elif event["type"] == "COLLECT_FROM_ALL":
            for p in game.players:
                if p.id != player.id:
                    actions["cash_changes"][p.id] = -event["value"]
            actions["cash_changes"][player.id] = event["value"] * (len(game.players) - 1)

        elif event["type"] == "SKIP_BUY":
            actions["skip_buy"] = True

        elif event["type"] == "MOVE_BACK":
            new_pos = max(0, player.position - event["value"])
            actions["position_changes"][player.id] = new_pos

        elif event["type"] == "MARKET_CRASH":
            actions["special"] = "MARKET_CRASH"

        elif event["type"] == "BULL_MARKET":
            actions["special"] = "BULL_MARKET"

        return actions
