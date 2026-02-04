"""Event manager - deck management and effect resolution with repository integration."""

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import ChaosLevel

# Aggressive event indices (STEAL, SWAP, REMOVE_UPGRADE, CLONE, FORCE_BUY, ALL_SKIP)
CHAOS_AGGRESSIVE_INDICES = {18, 19, 22, 24, 25, 34}


class EventManager:
    """Manages event deck with atomic persistence via repository."""

    def __init__(self, repository: "GameRepository") -> None:
        """Initialize event manager with repository."""
        self.repository = repository

    @staticmethod
    def initialize_deck(game: "GameSession") -> None:
        """Initialize and shuffle the event deck. Chaos level affects composition."""
        chaos = (
            getattr(game.settings, "chaos_level", ChaosLevel.NORMAL)
            if game.settings
            else ChaosLevel.NORMAL
        )

        if chaos == ChaosLevel.CHILL:
            deck = [i for i in range(len(SASTA_EVENTS)) if i not in CHAOS_AGGRESSIVE_INDICES]
        elif chaos == ChaosLevel.CHAOS:
            deck = list(range(len(SASTA_EVENTS)))
            deck.extend([i for i in CHAOS_AGGRESSIVE_INDICES if i < len(SASTA_EVENTS)])
        else:
            deck = list(range(len(SASTA_EVENTS)))

        random.shuffle(deck)
        game.event_deck = deck
        game.used_event_deck = []

    @staticmethod
    def ensure_capacity(game: "GameSession", count: int = 3) -> None:
        """Reshuffle discard pile if deck runs low."""
        if len(game.event_deck) < count and game.used_event_deck:
            game.event_deck.extend(game.used_event_deck)
            game.used_event_deck = []
            random.shuffle(game.event_deck)

    @staticmethod
    def draw_event(game: "GameSession") -> dict[str, Any] | None:
        """Draw next event from deck."""
        EventManager.ensure_capacity(game, 1)
        if not game.event_deck:
            return None
        event_idx = game.event_deck.pop(0)
        game.used_event_deck.append(event_idx)
        return SASTA_EVENTS[event_idx]

    async def apply_effect(
        self, game: "GameSession", player: "Player", event: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply event effect with atomic repository updates.
        Returns action dict for orchestrator.
        """
        actions: dict[str, Any] = {"cash_changes": {}, "position_changes": {}, "special": None}
        effect_type = event["type"]
        value = event.get("value", 0)

        if effect_type == "CASH_GAIN":
            player.cash += value
            await self.repository.update_player_cash(player.id, player.cash)
            actions["cash_changes"][player.id] = value

        elif effect_type == "CASH_LOSS":
            player.cash -= value
            await self.repository.update_player_cash(player.id, player.cash)
            actions["cash_changes"][player.id] = -value

        elif effect_type == "COLLECT_FROM_ALL":
            for p in game.players:
                if p.id != player.id:
                    p.cash -= value
                    await self.repository.update_player_cash(p.id, p.cash)
                    actions["cash_changes"][p.id] = -value
            total = value * (len(game.players) - 1)
            player.cash += total
            await self.repository.update_player_cash(player.id, player.cash)
            actions["cash_changes"][player.id] = total

        elif effect_type == "MOVE_BACK":
            new_pos = max(0, player.position - value)
            player.position = new_pos
            await self.repository.update_player_position(player.id, new_pos)
            actions["position_changes"][player.id] = new_pos

        elif effect_type == "MOVE_FORWARD":
            new_pos = (player.position + value) % len(game.board)
            player.position = new_pos
            await self.repository.update_player_position(player.id, new_pos)
            actions["position_changes"][player.id] = new_pos

        elif effect_type == "GO_TO_GO":
            go_pos = 0
            player.position = go_pos
            await self.repository.update_player_position(player.id, go_pos)
            actions["position_changes"][player.id] = go_pos

        elif effect_type == "TELEPORT_UNOWNED":
            unowned = [t for t in game.board if t.type.value == "PROPERTY" and not t.owner_id]
            if unowned:
                target_tile = random.choice(unowned)
                player.position = target_tile.position
                await self.repository.update_player_position(player.id, target_tile.position)
                actions["position_changes"][player.id] = target_tile.position

        elif effect_type == "STEAL_FROM_RICHEST":
            richest = max(game.players, key=lambda p: p.cash)
            if richest.id != player.id:
                amount = min(value, richest.cash)
                richest.cash -= amount
                player.cash += amount
                await self.repository.update_player_cash(richest.id, richest.cash)
                await self.repository.update_player_cash(player.id, player.cash)
                actions["cash_changes"][richest.id] = -amount
                actions["cash_changes"][player.id] = amount

        elif effect_type == "SWAP_CASH":
            other_players = [p for p in game.players if p.id != player.id]
            if other_players:
                target_player = random.choice(other_players)
                player.cash, target_player.cash = target_player.cash, player.cash
                await self.repository.update_player_cash(player.id, player.cash)
                await self.repository.update_player_cash(target_player.id, target_player.cash)
                actions["cash_changes"][player.id] = target_player.cash - player.cash
                actions["cash_changes"][target_player.id] = player.cash - target_player.cash

        elif effect_type == "MARKET_CRASH":
            game.rent_multiplier = 0.5
            actions["special"] = "MARKET_CRASH"

        elif effect_type == "BULL_MARKET":
            game.rent_multiplier = 1.5
            actions["special"] = "BULL_MARKET"

        elif effect_type == "HYPERINFLATION":
            actions["special"] = "HYPERINFLATION"

        elif effect_type == "FREE_UPGRADE":
            actions["special"] = "FREE_UPGRADE"

        elif effect_type == "REMOVE_UPGRADE":
            actions["special"] = "REMOVE_UPGRADE"

        elif effect_type == "BLOCK_TILE":
            actions["special"] = "BLOCK_TILE"
            actions["block_rounds"] = value

        elif effect_type == "SKIP_BUY":
            actions["skip_buy"] = True

        elif effect_type == "SKIP_TURN":
            player.active_buff = "SKIP_TURN"
            await self.repository.update_player_buff(player.id, "SKIP_TURN")
            actions["special"] = "SKIP_TURN"

        elif effect_type == "SKIP_MOVE":
            player.skip_next_move = True
            await self.repository.update_player_skip_next_move(player.id, True)
            actions["special"] = "SKIP_MOVE"

        elif effect_type == "DOUBLE_RENT":
            player.double_rent_next_turn = True
            await self.repository.update_player_double_rent_next_turn(player.id, True)
            actions["special"] = "DOUBLE_RENT"

        elif effect_type == "REVEAL_CASH":
            other_players = [p for p in game.players if p.id != player.id]
            if other_players:
                target_player = random.choice(other_players)
                actions["revealed_player"] = {
                    "id": target_player.id,
                    "name": target_player.name,
                    "cash": target_player.cash,
                }

        elif effect_type == "ALL_SKIP_TURN":
            for p in game.players:
                p.active_buff = "SKIP_TURN"
            actions["special"] = "ALL_SKIP_TURN"

        elif effect_type == "MOVE_TO_PREVIOUS":
            new_pos = player.previous_position
            player.position = new_pos
            await self.repository.update_player_position(player.id, new_pos)
            actions["position_changes"][player.id] = new_pos

        elif effect_type == "CLONE_UPGRADE":
            actions["special"] = "CLONE_UPGRADE"
            actions["requires_decision"] = True

        elif effect_type == "FORCE_BUY":
            actions["special"] = "FORCE_BUY"
            actions["force_buy_multiplier"] = value / 100
            actions["requires_decision"] = True

        elif effect_type == "FREE_LANDING":
            actions["special"] = "FREE_LANDING"
            actions["free_rounds"] = value
            actions["requires_decision"] = True

        if actions["special"]:
            await self.repository.update(game)

        return actions
