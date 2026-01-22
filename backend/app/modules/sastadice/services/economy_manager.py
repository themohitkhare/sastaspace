"""Economy manager for financial operations and bankruptcy logic."""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession, Player



class EconomyManager:
    """Handles all money operations and bankruptcy logic."""

    def __init__(self, repository: "GameRepository"):
        self.repository = repository

    async def charge_player(
        self,
        game: "GameSession",
        player: "Player",
        amount: int,
        creditor: Optional["Player"] = None,
    ) -> dict:
        """Charge a player amount. Returns dict with actions needed."""
        if amount <= 0:
            return {"action": "none"}

        if player.cash >= amount:
            player.cash -= amount
            if creditor:
                creditor.cash += amount
                await self.repository.update_player_cash(creditor.id, creditor.cash)
            await self.repository.update_player_cash(player.id, player.cash)
            return {"action": "charged", "amount": amount}

        needed = amount - player.cash
        raised = await self.auto_liquidate(game, player, needed)

        if player.cash + raised >= amount:
            player.cash -= amount
            if creditor:
                creditor.cash += amount
                await self.repository.update_player_cash(creditor.id, creditor.cash)
            await self.repository.update_player_cash(player.id, player.cash)
            return {"action": "charged_after_liquidation", "amount": amount, "raised": raised}
        else:
            await self.process_bankruptcy(game, player, creditor)
            return {"action": "bankrupt", "creditor_id": creditor.id if creditor else None}

    async def auto_liquidate(
        self, game: "GameSession", player: "Player", needed: int
    ) -> int:
        """Attempt to raise cash by downgrading/selling assets. Returns amount raised."""
        raised = 0

        upgraded_tiles = [
            t
            for t in game.board
            if t.owner_id == player.id and t.upgrade_level > 0
        ]
        upgraded_tiles.sort(key=lambda x: x.upgrade_level, reverse=True)

        for tile in upgraded_tiles:
            while tile.upgrade_level > 0 and raised < needed:
                refund = tile.price if tile.upgrade_level == 2 else tile.price // 2
                tile.upgrade_level -= 1
                player.cash += refund
                raised += refund

                if raised >= needed:
                    break

        if raised >= needed:
            await self.repository.save_board(game.id, game.board)
            return raised

        properties = [t for t in game.board if t.owner_id == player.id]
        properties.sort(key=lambda x: x.price)

        for tile in properties:
            if raised >= needed:
                break

            sell_value = tile.price // 2
            if tile.upgrade_level == 2:
                extra_refund = tile.price + (tile.price // 2)
            elif tile.upgrade_level == 1:
                extra_refund = tile.price // 2
            else:
                extra_refund = 0

            player.cash += sell_value + extra_refund
            raised += sell_value + extra_refund
            tile.owner_id = None
            tile.upgrade_level = 0

        await self.repository.save_board(game.id, game.board)
        return raised

    async def process_bankruptcy(
        self,
        game: "GameSession",
        debtor: "Player",
        creditor: Optional["Player"] = None,
    ) -> None:
        """Handle bankruptcy: asset transfer or seizure."""
        debtor.is_bankrupt = True
        remaining_cash = max(0, debtor.cash)
        debtor.cash = 0

        debtor_properties = [t for t in game.board if t.owner_id == debtor.id]

        if creditor:
            for tile in debtor_properties:
                tile.owner_id = creditor.id
            creditor.cash += remaining_cash
            await self.repository.update_player_cash(creditor.id, creditor.cash)
            game.last_event_message = (
                f"💀 {debtor.name} went BANKRUPT! Assets seized by {creditor.name}."
            )
        else:
            for tile in debtor_properties:
                tile.owner_id = None
                tile.upgrade_level = 0
            game.last_event_message = (
                f"💀 {debtor.name} went BANKRUPT! Assets seized by Bank."
            )

        await self.repository.update_player_bankrupt(debtor.id, True)
        await self.repository.update_player_cash(debtor.id, 0)
        await self.repository.save_board(game.id, game.board)

    async def check_end_conditions(self, game_id: str) -> bool:
        """Check for bankruptcy and game end. Returns True if game ended."""
        return False

    async def handle_buy_property(
        self, game: "GameSession", player_id: str
    ) -> tuple[bool, str, Optional[str], Optional[int]]:
        """Handle buying a property. Returns (success, message, tile_name, price)."""
        from app.modules.sastadice.schemas import TurnPhase

        if game.turn_phase != TurnPhase.DECISION:
            return False, "Cannot buy property now", None, None

        if not game.pending_decision or game.pending_decision.type != "BUY":
            return False, "No property to buy", None, None

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "Player not found", None, None

        tile_id = game.pending_decision.tile_id
        if not tile_id:
            return False, "Invalid tile ID in decision", None, None

        price = game.pending_decision.price

        if player.cash < price:
            return (
                False,
                f"Not enough cash. Need ${price}, have ${player.cash}",
                None,
                None,
            )

        player.cash -= price
        player.properties.append(tile_id)
        await self.repository.update_player_cash(player_id, player.cash)
        await self.repository.update_player_properties(player_id, player.properties)
        await self.repository.update_tile_owner(tile_id, player_id)

        tile = next((t for t in game.board if t.id == tile_id), None)
        tile_name = tile.name if tile else "property"

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN

        return True, f"Bought '{tile_name}' for ${price}", tile_name, price

    async def handle_upgrade(
        self, game: "GameSession", player_id: str, payload: dict, turn_manager
    ) -> tuple[bool, str, Optional[str]]:
        """Handle property upgrade. Returns (success, message, level_name)."""
        from app.modules.sastadice.schemas import TileType

        tile_id = payload.get("tile_id")
        if not tile_id:
            return False, "Tile ID required", None

        tile = next((t for t in game.board if t.id == tile_id), None)
        if not tile or tile.type != TileType.PROPERTY:
            return False, "Invalid property", None

        if tile.owner_id != player_id:
            return False, "You don't own this property", None

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "Player not found", None

        if not tile.color or not turn_manager.owns_full_set(player, tile.color, game.board):
            return False, "You must own the full color set to upgrade", None

        if tile.upgrade_level >= 2:
            return False, "Max upgrade level reached", None

        upgrade_cost = tile.price * (2 if tile.upgrade_level == 1 else 1)

        if player.cash < upgrade_cost:
            return False, f"Insufficient funds (Need ${upgrade_cost})", None

        player.cash -= upgrade_cost
        tile.upgrade_level += 1

        level_name = "SCRIPT KIDDIE" if tile.upgrade_level == 1 else "1337 HAXXOR"

        await self.repository.update_player_cash(player.id, player.cash)
        await self.repository.save_board(game.id, game.board)

        return True, f"Upgraded to {level_name}", level_name

    async def handle_downgrade(
        self, game: "GameSession", player_id: str, payload: dict
    ) -> tuple[bool, str, Optional[int]]:
        """Handle property downgrade. Returns (success, message, refund)."""
        from app.modules.sastadice.schemas import TileType

        tile_id = payload.get("tile_id")
        if not tile_id:
            return False, "Tile ID required", None

        tile = next((t for t in game.board if t.id == tile_id), None)
        if not tile or tile.type != TileType.PROPERTY:
            return False, "Invalid property", None

        if tile.owner_id != player_id:
            return False, "You don't own this property", None

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "Player not found", None

        if tile.upgrade_level <= 0:
            return False, "No upgrades to sell", None

        original_cost = tile.price * 2 if tile.upgrade_level == 2 else tile.price
        refund = original_cost // 2

        prev_level_name = "1337 HAXXOR" if tile.upgrade_level == 2 else "SCRIPT KIDDIE"
        tile.upgrade_level -= 1
        player.cash += refund

        await self.repository.update_player_cash(player.id, player.cash)
        await self.repository.save_board(game.id, game.board)

        return True, f"Sold upgrade for ${refund}", refund

    def determine_winner(self, game: "GameSession") -> Optional[dict]:
        """Determine the winner of the game."""
        active_players = [p for p in game.players if p.cash >= 0]

        if len(active_players) == 1:
            winner = active_players[0]
            return {
                "name": winner.name,
                "cash": winner.cash,
                "properties": len(winner.properties),
            }
        elif len(active_players) == 0:
            richest = max(game.players, key=lambda x: x.cash)
            return {
                "name": richest.name,
                "cash": richest.cash,
                "properties": len(richest.properties),
            }
        else:
            leader = max(active_players, key=lambda x: x.cash)
            return {
                "name": leader.name,
                "cash": leader.cash,
                "properties": len(leader.properties),
                "status": "in_progress",
            }
