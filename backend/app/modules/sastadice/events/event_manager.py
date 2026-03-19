"""Event manager - deck management and effect resolution with repository integration."""

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import ChaosLevel

# Aggressive event types (used for chaos deck composition)
AGGRESSIVE_TYPES = {
    "STEAL_FROM_RICHEST",
    "SWAP_CASH",
    "REMOVE_UPGRADE",
    "CLONE_UPGRADE",
    "FORCE_BUY",
    "ALL_SKIP_TURN",
}

# Indices of aggressive events, derived from event definitions
CHAOS_AGGRESSIVE_INDICES = {
    idx for idx, event in enumerate(SASTA_EVENTS) if event.get("type") in AGGRESSIVE_TYPES
}


class EventManager:
    """Manages event deck with atomic persistence via repository."""

    def __init__(self, repository: "GameRepository") -> None:
        """Initialize event manager with repository."""
        self.repository = repository
        # Strategy-style mapping from effect type to handler coroutine
        self._effect_handlers = {
            "CASH_GAIN": self._handle_cash_gain,
            "CASH_LOSS": self._handle_cash_loss,
            "COLLECT_FROM_ALL": self._handle_collect_from_all,
            "MOVE_BACK": self._handle_move_back,
            "MOVE_FORWARD": self._handle_move_forward,
            "GO_TO_GO": self._handle_go_to_go,
            "TELEPORT_UNOWNED": self._handle_teleport_unowned,
            "STEAL_FROM_RICHEST": self._handle_steal_from_richest,
            "SWAP_CASH": self._handle_swap_cash,
            "MARKET_CRASH": self._handle_market_crash,
            "BULL_MARKET": self._handle_bull_market,
            "HYPERINFLATION": self._handle_hyperinflation,
            "FREE_UPGRADE": self._handle_free_upgrade,
            "REMOVE_UPGRADE": self._handle_remove_upgrade,
            "BLOCK_TILE": self._handle_block_tile,
            "SKIP_BUY": self._handle_skip_buy,
            "SKIP_TURN": self._handle_skip_turn,
            "SKIP_MOVE": self._handle_skip_move,
            "DOUBLE_RENT": self._handle_double_rent,
            "REVEAL_CASH": self._handle_reveal_cash,
            "ALL_SKIP_TURN": self._handle_all_skip_turn,
            "MOVE_TO_PREVIOUS": self._handle_move_to_previous,
            "CLONE_UPGRADE": self._handle_clone_upgrade,
            "FORCE_BUY": self._handle_force_buy,
            "FREE_LANDING": self._handle_free_landing,
            "WEALTH_TAX": self._handle_wealth_tax,
            "AUDIT_SEASON": self._handle_audit_season,
            "BAILOUT_PACKAGE": self._handle_bailout_package,
        }

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
        handler = self._effect_handlers.get(effect_type)
        if handler is not None:
            await handler(game, player, event, actions)

        if actions["special"]:
            await self.repository.update(game)

        return actions

    # === Effect handlers ===

    async def _handle_cash_gain(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        player.cash += value
        await self.repository.update_player_cash(player.id, player.cash)
        actions["cash_changes"][player.id] = value

    async def _handle_cash_loss(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        player.cash -= value
        await self.repository.update_player_cash(player.id, player.cash)
        actions["cash_changes"][player.id] = -value

    async def _handle_collect_from_all(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        for p in game.players:
            if p.id != player.id:
                p.cash -= value
                await self.repository.update_player_cash(p.id, p.cash)
                actions["cash_changes"][p.id] = -value
        total = value * (len(game.players) - 1)
        player.cash += total
        await self.repository.update_player_cash(player.id, player.cash)
        actions["cash_changes"][player.id] = total

    async def _handle_move_back(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        new_pos = max(0, player.position - value)
        player.position = new_pos
        await self.repository.update_player_position(player.id, new_pos)
        actions["position_changes"][player.id] = new_pos

    async def _handle_move_forward(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        new_pos = (player.position + value) % len(game.board)
        player.position = new_pos
        await self.repository.update_player_position(player.id, new_pos)
        actions["position_changes"][player.id] = new_pos

    async def _handle_go_to_go(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        go_pos = 0
        player.position = go_pos
        await self.repository.update_player_position(player.id, go_pos)
        actions["position_changes"][player.id] = go_pos

    async def _handle_teleport_unowned(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        unowned = [t for t in game.board if t.type.value == "PROPERTY" and not t.owner_id]
        if unowned:
            target_tile = random.choice(unowned)
            player.position = target_tile.position
            await self.repository.update_player_position(player.id, target_tile.position)
            actions["position_changes"][player.id] = target_tile.position

    async def _handle_steal_from_richest(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        richest = max(game.players, key=lambda p: p.cash)
        if richest.id != player.id:
            amount = min(value, richest.cash)
            richest.cash -= amount
            player.cash += amount
            await self.repository.update_player_cash(richest.id, richest.cash)
            await self.repository.update_player_cash(player.id, player.cash)
            actions["cash_changes"][richest.id] = -amount
            actions["cash_changes"][player.id] = amount

    async def _handle_swap_cash(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        """Swap cash with a random player: transfer 50% of the difference, capped at $500."""
        max_transfer = 500
        other_players = [p for p in game.players if p.id != player.id]
        if other_players:
            target_player = random.choice(other_players)
            original_player_cash = player.cash
            original_target_cash = target_player.cash

            # Calculate 50% of the difference, capped at $500 in either direction
            difference = target_player.cash - player.cash
            transfer = difference // 2
            transfer = max(-max_transfer, min(max_transfer, transfer))

            player.cash += transfer
            target_player.cash -= transfer

            await self.repository.update_player_cash(player.id, player.cash)
            await self.repository.update_player_cash(target_player.id, target_player.cash)
            actions["cash_changes"][player.id] = player.cash - original_player_cash
            actions["cash_changes"][target_player.id] = target_player.cash - original_target_cash

    async def _handle_market_crash(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        game.rent_multiplier = 0.5
        actions["special"] = "MARKET_CRASH"

    async def _handle_bull_market(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        game.rent_multiplier = 1.5
        actions["special"] = "BULL_MARKET"

    async def _handle_hyperinflation(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        actions["special"] = "HYPERINFLATION"

    async def _handle_free_upgrade(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        actions["special"] = "FREE_UPGRADE"

    async def _handle_remove_upgrade(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        actions["special"] = "REMOVE_UPGRADE"

    async def _handle_block_tile(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        actions["special"] = "BLOCK_TILE"
        actions["block_rounds"] = value

    async def _handle_skip_buy(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        actions["skip_buy"] = True

    async def _handle_skip_turn(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        player.active_buff = "SKIP_TURN"
        await self.repository.update_player_buff(player.id, "SKIP_TURN")
        actions["special"] = "SKIP_TURN"

    async def _handle_skip_move(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        player.skip_next_move = True
        await self.repository.update_player_skip_next_move(player.id, True)
        actions["special"] = "SKIP_MOVE"

    async def _handle_double_rent(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        player.double_rent_next_turn = True
        await self.repository.update_player_double_rent_next_turn(player.id, True)
        actions["special"] = "DOUBLE_RENT"

    async def _handle_reveal_cash(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        other_players = [p for p in game.players if p.id != player.id]
        if other_players:
            target_player = random.choice(other_players)
            actions["revealed_player"] = {
                "id": target_player.id,
                "name": target_player.name,
                "cash": target_player.cash,
            }

    async def _handle_all_skip_turn(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        for p in game.players:
            p.active_buff = "SKIP_TURN"
        actions["special"] = "ALL_SKIP_TURN"

    async def _handle_move_to_previous(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        new_pos = player.previous_position
        player.position = new_pos
        await self.repository.update_player_position(player.id, new_pos)
        actions["position_changes"][player.id] = new_pos

    async def _handle_clone_upgrade(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        actions["special"] = "CLONE_UPGRADE"
        actions["requires_decision"] = True

    async def _handle_force_buy(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        actions["special"] = "FORCE_BUY"
        actions["force_buy_multiplier"] = value / 100 if value else 0
        actions["requires_decision"] = True

    async def _handle_free_landing(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        value = event.get("value", 0)
        actions["special"] = "FREE_LANDING"
        actions["free_rounds"] = value
        actions["requires_decision"] = True

    async def _handle_wealth_tax(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        """Players above median cash lose 10% of excess; redistributed to those below median."""
        import statistics

        active_players = [p for p in game.players if not p.is_bankrupt]
        if len(active_players) < 2:
            return

        cash_values = sorted([p.cash for p in active_players])
        median_cash = statistics.median(cash_values)

        total_taxed = 0
        above_median = []
        below_median = []

        for p in active_players:
            if p.cash > median_cash:
                above_median.append(p)
            elif p.cash < median_cash:
                below_median.append(p)

        # Tax those above median: 10% of excess
        tax_rate = (event.get("value", 10)) / 100
        for p in above_median:
            excess = p.cash - int(median_cash)
            tax = int(excess * tax_rate)
            if tax > 0:
                p.cash -= tax
                total_taxed += tax
                await self.repository.update_player_cash(p.id, p.cash)
                actions["cash_changes"][p.id] = actions["cash_changes"].get(p.id, 0) - tax

        # Redistribute equally to those below median
        if below_median and total_taxed > 0:
            per_player = total_taxed // len(below_median)
            remainder = total_taxed - (per_player * len(below_median))
            for i, p in enumerate(below_median):
                bonus = per_player + (1 if i < remainder else 0)
                p.cash += bonus
                await self.repository.update_player_cash(p.id, p.cash)
                actions["cash_changes"][p.id] = actions["cash_changes"].get(p.id, 0) + bonus

        actions["special"] = "WEALTH_TAX"

    async def _handle_audit_season(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        """Reveal all property rent values on the board for N rounds."""
        rounds = event.get("value", 2)
        actions["special"] = "AUDIT_SEASON"
        actions["audit_until_round"] = game.current_round + rounds

    async def _handle_bailout_package(
        self, game: "GameSession", player: "Player", event: dict[str, Any], actions: dict[str, Any]
    ) -> None:
        """Give $500 to the poorest non-bankrupt player. Ties broken by fewer properties."""
        bailout_amount = event.get("value", 500)
        active_players = [p for p in game.players if not p.is_bankrupt]
        if not active_players:
            return

        # Sort by cash ascending, then by property count ascending (fewer = poorer)
        poorest = min(active_players, key=lambda p: (p.cash, len(p.properties)))
        poorest.cash += bailout_amount
        await self.repository.update_player_cash(poorest.id, poorest.cash)
        actions["cash_changes"][poorest.id] = (
            actions["cash_changes"].get(poorest.id, 0) + bailout_amount
        )
        actions["special"] = "BAILOUT_PACKAGE"
        actions["bailout_recipient"] = {"id": poorest.id, "name": poorest.name}
