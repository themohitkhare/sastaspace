"""Action dispatcher with validation layer for all game actions."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import Player, Tile
    from app.modules.sastadice.services.auction_manager import AuctionManager
    from app.modules.sastadice.services.economy_manager import EconomyManager
    from app.modules.sastadice.services.jail_manager import JailManager
    from app.modules.sastadice.services.trade_manager import TradeManager
    from app.modules.sastadice.services.turn_coordinator import TurnCoordinator
    from app.modules.sastadice.services.turn_manager import TurnManager

from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import (
    ActionResult,
    ActionType,
    GameSession,
    TileType,
    TurnPhase,
)


class ActionDispatcher:
    """Dispatches game actions with payload validation."""

    def __init__(
        self,
        repository: "GameRepository",
        economy_manager: "EconomyManager",
        auction_manager: "AuctionManager",
        trade_manager: "TradeManager",
        turn_coordinator: "TurnCoordinator",
        turn_manager: "TurnManager",
        jail_manager: "JailManager | None" = None,
        roll_dice_callback: Any = None,
        handle_tile_landing_callback: Any = None,
        send_to_jail_callback: Any = None,
    ) -> None:
        self.repository = repository
        self.economy_manager = economy_manager
        self.auction_manager = auction_manager
        self.trade_manager = trade_manager
        self.turn_coordinator = turn_coordinator
        self.turn_manager = turn_manager
        self.jail_manager = jail_manager
        self.roll_dice_callback = roll_dice_callback
        self.handle_tile_landing_callback = handle_tile_landing_callback
        self.send_to_jail_callback_fn = send_to_jail_callback

    def _validate_payload(
        self, action_type: ActionType, payload: dict[str, Any]
    ) -> tuple[bool, dict[str, Any], str | None]:
        """
        Validate payload data with Pydantic-like checks.
        Returns (is_valid, validated_payload, error_message).
        """
        validated = payload.copy()

        match action_type:
            case ActionType.BID:
                if "amount" not in validated:
                    return False, {}, "Bid amount required"
                amount = validated.get("amount")
                if not isinstance(amount, int) or amount < 0:
                    return False, {}, "Bid amount must be a non-negative integer"
                validated["amount"] = int(amount)

            case ActionType.UPGRADE | ActionType.DOWNGRADE | ActionType.BLOCK_TILE:
                if "tile_id" not in validated:
                    return False, {}, f"{action_type.value} requires tile_id"
                if not isinstance(validated["tile_id"], str):
                    return False, {}, "tile_id must be a string"

            case ActionType.BUY_BUFF:
                if "buff_id" not in validated:
                    return False, {}, "buff_id required"
                if not isinstance(validated["buff_id"], str):
                    return False, {}, "buff_id must be a string"

            case ActionType.PROPOSE_TRADE:
                required = ["target_id"]
                for field in required:
                    if field not in validated:
                        return False, {}, f"{field} required for trade"
                if not isinstance(validated["target_id"], str):
                    return False, {}, "target_id must be a string"

            case ActionType.ACCEPT_TRADE | ActionType.DECLINE_TRADE | ActionType.CANCEL_TRADE:
                if "trade_id" not in validated:
                    return False, {}, "trade_id required"
                if not isinstance(validated["trade_id"], str):
                    return False, {}, "trade_id must be a string"

        return True, validated, None

    async def dispatch(
        self,
        game: GameSession,
        player_id: str,
        action_type: ActionType,
        payload: dict[str, Any],
    ) -> ActionResult:
        """
        Dispatch action to appropriate handler with validation.
        Returns ActionResult.
        """
        is_valid, validated_payload, error = self._validate_payload(action_type, payload)
        if not is_valid:
            return ActionResult(success=False, message=error or "Invalid payload")
        match action_type:
            case ActionType.ROLL_DICE:
                return await self._handle_roll_dice(game, player_id)
            case ActionType.BUY_PROPERTY:
                return await self._handle_buy_property(game, player_id)
            case ActionType.PASS_PROPERTY:
                return await self._handle_pass_property(game, player_id)
            case ActionType.BID:
                return await self._handle_bid(game, player_id, validated_payload)
            case ActionType.RESOLVE_AUCTION:
                return await self._resolve_auction(game)
            case ActionType.UPGRADE:
                return await self._handle_upgrade(game, player_id, validated_payload)
            case ActionType.DOWNGRADE:
                return await self._handle_downgrade(game, player_id, validated_payload)
            case ActionType.BUY_BUFF:
                return await self._handle_buy_buff(game, player_id, validated_payload)
            case ActionType.BLOCK_TILE:
                return await self._handle_block_tile(game, player_id, validated_payload)
            case ActionType.PROPOSE_TRADE:
                return await self._handle_propose_trade(game, player_id, validated_payload)
            case ActionType.ACCEPT_TRADE:
                return await self._handle_accept_trade(game, player_id, validated_payload)
            case ActionType.DECLINE_TRADE:
                return await self._handle_decline_trade(game, player_id, validated_payload)
            case ActionType.CANCEL_TRADE:
                return await self._handle_cancel_trade(game, player_id, validated_payload)
            case ActionType.END_TURN:
                return await self._handle_end_turn(game, player_id)
            case ActionType.BUY_RELEASE:
                return await self._handle_buy_release(game, player_id)
            case ActionType.ROLL_FOR_DOUBLES:
                return await self._handle_roll_for_doubles(game, player_id)
            case ActionType.EVENT_CLONE_UPGRADE:
                return await self._handle_event_clone_upgrade(game, player_id, validated_payload)
            case ActionType.EVENT_FORCE_BUY:
                return await self._handle_event_force_buy(game, player_id, validated_payload)
            case ActionType.EVENT_FREE_LANDING:
                return await self._handle_event_free_landing(game, player_id, validated_payload)
            case _:
                return ActionResult(success=False, message=f"Unknown action: {action_type}")

    async def _handle_roll_dice(self, game: GameSession, player_id: str) -> ActionResult:
        try:
            if self.roll_dice_callback:
                dice_result = await self.roll_dice_callback(game.id, player_id)
            else:
                dice_result = await self.turn_coordinator.roll_dice(
                    game,
                    player_id,
                    self.send_to_jail_callback_fn or self._send_to_jail_callback,
                    self.handle_tile_landing_callback or self._handle_tile_landing_callback,
                )

            updated_game = await self._get_game(game.id)
            player_idx = next(i for i, p in enumerate(updated_game.players) if p.id == player_id)
            return ActionResult(
                success=True,
                message=updated_game.last_event_message or "Dice rolled",
                data={
                    **dice_result.model_dump(),
                    "new_position": updated_game.players[player_idx].position,
                    "turn_phase": updated_game.turn_phase.value,
                    "pending_decision": updated_game.pending_decision.model_dump()
                    if updated_game.pending_decision
                    else None,
                },
            )
        except ValueError as e:
            return ActionResult(success=False, message=str(e))

    async def _handle_buy_property(self, game: GameSession, player_id: str) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        success, message, tile_name, price = await self.economy_manager.handle_buy_property(
            game, player_id
        )

        if success and tile_name and price:
            game.last_event_message = f"🏠 Bought '{tile_name}' for ${price}!"
            await self.repository.update(game)

        return ActionResult(success=success, message=message)

    async def _handle_pass_property(self, game: GameSession, player_id: str) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        if game.turn_phase != TurnPhase.DECISION:
            return ActionResult(success=False, message="Cannot pass now")

        if (
            game.settings.enable_auctions
            and game.pending_decision
            and game.pending_decision.type == "BUY"
        ):
            tile_id = game.pending_decision.tile_id
            if not tile_id:
                game.pending_decision = None
                game.turn_phase = TurnPhase.POST_TURN
                game.last_event_message = "Passed on decision."
                await self.repository.update(game)
                return ActionResult(success=True, message="Passed on decision")

            tile = next((t for t in game.board if t.id == tile_id), None)

            if tile and tile.type == TileType.PROPERTY and not tile.owner_id:
                self.auction_manager.start_auction(game, tile, auction_duration=10)
                await self.repository.update(game)
                return ActionResult(success=True, message=f"Auction started for {tile.name}")

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        game.last_event_message = "Passed on decision."
        await self.repository.update(game)

        return ActionResult(success=True, message="Passed on decision")

    async def _handle_bid(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        if game.turn_phase != TurnPhase.AUCTION or not game.auction_state:
            return ActionResult(success=False, message="No active auction")

        amount = payload.get("amount")
        if not amount:
            return ActionResult(success=False, message="Bid amount required")

        if self.auction_manager.check_auction_timeout(game.auction_state):
            return await self._resolve_auction(game)

        success, message = self.auction_manager.place_bid(game, player_id, amount)
        if success:
            await self.repository.update(game)
        return ActionResult(success=success, message=message)

    async def _handle_upgrade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        success, message, level_name = await self.economy_manager.handle_upgrade(
            game, player_id, payload, self.turn_manager
        )

        if success and level_name:
            tile_id = payload.get("tile_id")
            tile = next((t for t in game.board if t.id == tile_id), None)
            player = next((p for p in game.players if p.id == player_id), None)
            if tile and player:
                game.last_event_message = f"💻 {player.name} upgraded {tile.name} to {level_name}!"
            await self.repository.update(game)

        return ActionResult(success=success, message=message)

    async def _handle_downgrade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        success, message, refund = await self.economy_manager.handle_downgrade(
            game, player_id, payload
        )

        if success and refund:
            tile_id = payload.get("tile_id")
            tile = next((t for t in game.board if t.id == tile_id), None)
            player = next((p for p in game.players if p.id == player_id), None)
            if tile and player:
                prev_level_name = "1337 HAXXOR" if tile.upgrade_level == 0 else "SCRIPT KIDDIE"
                game.last_event_message = (
                    f"💸 {player.name} sold {prev_level_name} upgrade on {tile.name} for ${refund}"
                )
            await self.repository.update(game)

        return ActionResult(success=success, message=message)

    async def _handle_buy_buff(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        if (
            game.turn_phase != TurnPhase.DECISION
            or not game.pending_decision
            or game.pending_decision.type != "MARKET"
        ):
            return ActionResult(success=False, message="Not in Market")

        buff_id = payload.get("buff_id")
        event_data = game.pending_decision.event_data or {}
        buffs = event_data.get("buffs", [])
        selected_buff = next((b for b in buffs if b["id"] == buff_id), None)

        if not selected_buff:
            return ActionResult(success=False, message="Invalid buff")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        if player.cash < selected_buff["cost"]:
            return ActionResult(success=False, message="Insufficient funds")

        if buff_id == "PEEK":
            needed = 3
            self.turn_manager.ensure_deck_capacity(game, needed)
            preview_indices = game.event_deck[:needed]
            preview_names = [str(SASTA_EVENTS[idx]["name"]) for idx in preview_indices]

            player.cash -= selected_buff["cost"]
            await self.repository.update_player_cash(player.id, player.cash)

            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN

            msg = f"🔎 Insider Info! Next Events: {', '.join(preview_names)}"
            game.last_event_message = msg
            await self.repository.update(game)
            return ActionResult(success=True, message=msg)

        player.cash -= selected_buff["cost"]
        player.active_buff = buff_id
        await self.repository.update_player_cash(player.id, player.cash)
        await self.repository.update_player_buff(player.id, buff_id)

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        game.last_event_message = f"🛒 {player.name} bought {selected_buff['name']}!"
        await self.repository.update(game)
        return ActionResult(success=True, message=f"Bought {selected_buff['name']}")

    async def _handle_block_tile(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        if game.turn_phase not in (TurnPhase.POST_TURN, TurnPhase.PRE_ROLL):
            return ActionResult(success=False, message="Cannot use DDoS in current phase")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        if player.active_buff != "DDOS":
            return ActionResult(success=False, message="You don't have the DDoS buff")

        target_tile_id = payload.get("tile_id")
        if not target_tile_id:
            return ActionResult(success=False, message="Target tile required")

        tile = next((t for t in game.board if t.id == target_tile_id), None)
        if not tile:
            return ActionResult(success=False, message="Invalid tile")

        tile.blocked_until_round = game.current_round + 1
        player.active_buff = None

        await self.repository.update_player_buff(player.id, None)
        await self.repository.save_board(game.id, game.board)

        game.last_event_message = (
            f"💀 DDoS ATTACK! {tile.name} disabled for 1 round by {player.name}!"
        )
        await self.repository.update(game)
        return ActionResult(success=True, message=f"Disabled {tile.name}")

    async def _handle_propose_trade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Can only propose trades on your turn")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        offer, error = self.trade_manager.create_trade_offer(game, player, payload)
        if error:
            return ActionResult(success=False, message=error)

        if offer:
            target_player = next((p for p in game.players if p.id == offer.target_id), None)
            game.active_trade_offers.append(offer)
            game.last_event_message = f"🤝 {player.name} proposed a trade to {target_player.name if target_player else 'Unknown'}!"
            await self.repository.update(game)
            return ActionResult(success=True, message="Trade offered")

        return ActionResult(success=False, message="Failed to create trade offer")

    async def _handle_accept_trade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade offer not found")

        if offer.target_id != player_id:
            return ActionResult(success=False, message="Not authorized to accept this trade")

        initiator = next((p for p in game.players if p.id == offer.initiator_id), None)
        player = next((p for p in game.players if p.id == player_id), None)

        if not initiator:
            game.active_trade_offers.remove(offer)
            await self.repository.update(game)
            return ActionResult(success=False, message="Initiator gone")

        if not player:
            game.active_trade_offers.remove(offer)
            await self.repository.update(game)
            return ActionResult(success=False, message="Player not found")

        validation_error = self.trade_manager.validate_trade_assets(game, offer, initiator, player)
        if validation_error:
            return ActionResult(success=False, message=validation_error)

        transfer_data = self.trade_manager.execute_trade_transfer(game, offer, initiator, player)

        initiator.cash = transfer_data["initiator_cash"]
        player.cash = transfer_data["target_cash"]

        await self.repository.update_player_cash(initiator.id, initiator.cash)
        await self.repository.update_player_cash(player.id, player.cash)

        initiator_to_target = transfer_data["property_transfers"]["initiator_to_target"]
        target_to_initiator = transfer_data["property_transfers"]["target_to_initiator"]

        for pid in initiator_to_target:
            tile = next((t for t in game.board if t.id == pid), None)
            if tile:
                tile.owner_id = player.id

        for pid in target_to_initiator:
            tile = next((t for t in game.board if t.id == pid), None)
            if tile:
                tile.owner_id = initiator.id

        initiator.properties = [
            p for p in initiator.properties if p not in initiator_to_target
        ] + target_to_initiator
        player.properties = [
            p for p in player.properties if p not in target_to_initiator
        ] + initiator_to_target

        await self.repository.save_board(game.id, game.board)
        await self.repository.update_player_properties(initiator.id, initiator.properties)
        await self.repository.update_player_properties(player.id, player.properties)

        game.active_trade_offers.remove(offer)
        game.last_event_message = f"🤝 Trade accepted between {initiator.name} and {player.name}!"
        await self.repository.update(game)
        return ActionResult(success=True, message="Trade completed")

    async def _handle_decline_trade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade not found")

        if offer.target_id != player_id:
            return ActionResult(success=False, message="Not authorized")

        player = next((p for p in game.players if p.id == player_id), None)
        game.active_trade_offers.remove(offer)
        player_name = player.name if player else "Unknown"
        game.last_event_message = f"🚫 {player_name} declined trade."
        await self.repository.update(game)
        return ActionResult(success=True, message="Declined")

    async def _handle_cancel_trade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade not found")

        if offer.initiator_id != player_id:
            return ActionResult(success=False, message="Not authorized")

        game.active_trade_offers.remove(offer)
        await self.repository.update(game)
        return ActionResult(success=True, message="Cancelled")

    async def _determine_winner_async(self, game: GameSession) -> dict[str, Any] | None:
        """Async wrapper for sync _determine_winner (for TurnCoordinator callback)."""
        return self._determine_winner(game)

    async def _handle_end_turn(self, game: GameSession, player_id: str) -> ActionResult:
        return await self.turn_coordinator.handle_end_turn(
            game,
            player_id,
            self._check_and_handle_end_conditions,
            self._determine_winner_async,
        )

    async def _handle_buy_release(self, game: GameSession, player_id: str) -> ActionResult:
        if not self.jail_manager:
            return ActionResult(success=False, message="Jail manager not available")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        success, message = self.jail_manager.attempt_bribe_release(game, player)
        if success:
            await self.repository.update_player_cash(player.id, player.cash)
            await self.repository.update_player_jail(player.id, False, 0)
            game.last_event_message = message
            await self.repository.update(game)

        return ActionResult(success=success, message=message)

    async def _handle_roll_for_doubles(self, game: GameSession, player_id: str) -> ActionResult:
        if not self.jail_manager:
            return ActionResult(success=False, message="Jail manager not available")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        escaped, dice1, dice2, message = self.jail_manager.roll_for_doubles(game, player)
        if escaped:
            await self.repository.update_player_cash(player.id, player.cash)
            await self.repository.update_player_jail(player.id, player.in_jail, player.jail_turns)
            game.last_event_message = message
            await self.repository.update(game)
            return ActionResult(
                success=True,
                message=message,
                data={"dice1": dice1, "dice2": dice2, "escaped": True},
            )
        else:
            await self.repository.update_player_jail(player.id, player.in_jail, player.jail_turns)
            await self.repository.update(game)
            return ActionResult(
                success=False,
                message=message,
                data={"dice1": dice1, "dice2": dice2, "escaped": False},
            )

    async def _resolve_auction(self, game: GameSession) -> ActionResult:
        success, message, winner_id, amount, prop_id = self.auction_manager.resolve_auction(game)

        if not success:
            return ActionResult(success=False, message=message)

        if winner_id and prop_id:
            winner = next((p for p in game.players if p.id == winner_id), None)
            if winner:
                winner.cash -= amount
                winner.properties.append(prop_id)
                await self.repository.update_player_cash(winner.id, winner.cash)
                await self.repository.update_player_properties(winner.id, winner.properties)
                await self.repository.update_tile_owner(prop_id, winner.id)

                tile = next((t for t in game.board if t.id == prop_id), None)
                if tile:
                    tile.owner_id = winner.id

        if (
            prop_id
            and game.bankruptcy_auction_queue
            and game.bankruptcy_auction_queue[0] == prop_id
        ):
            game.bankruptcy_auction_queue.pop(0)
            if game.bankruptcy_auction_queue:
                next_tile = next(
                    (t for t in game.board if t.id == game.bankruptcy_auction_queue[0]),
                    None,
                )
                if next_tile:
                    self.auction_manager.start_auction(game, next_tile, auction_duration=10)
                    game.last_event_message = (
                        f"🔨 State auction: {next_tile.name} from bankrupt player!"
                    )
            else:
                game.bankruptcy_auction_queue = []

        await self.repository.update(game)

        final_message = game.last_event_message or message
        return ActionResult(success=True, message=final_message)

    async def _get_game(self, game_id: str) -> GameSession:
        game = await self.repository.get_by_id(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        return game

    async def _send_to_jail_callback(self, game: GameSession, player: "Player") -> None:
        if self.jail_manager:
            self.jail_manager.send_to_jail(game, player)
            jail_pos = len(game.board) // 2
            await self.repository.update_player_position(player.id, jail_pos)

    async def _handle_event_clone_upgrade(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        source_tile_id = payload.get("source_tile_id")
        target_tile_id = payload.get("target_tile_id")

        if not source_tile_id or not target_tile_id:
            return ActionResult(success=False, message="Must specify source and target tiles")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        source_tile = next((t for t in game.board if t.id == source_tile_id), None)
        target_tile = next((t for t in game.board if t.id == target_tile_id), None)

        if not source_tile or not target_tile:
            return ActionResult(success=False, message="Tile not found")

        if source_tile.upgrade_level == 0:
            return ActionResult(success=False, message="Source property has no upgrades")

        if target_tile.owner_id != player_id:
            return ActionResult(success=False, message="You don't own the target property")

        if target_tile.type != TileType.PROPERTY:
            return ActionResult(success=False, message="Can only clone to properties")

        target_tile.upgrade_level = source_tile.upgrade_level
        await self.repository.save_board(game.id, game.board)

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        await self.repository.update(game)

        return ActionResult(
            success=True, message=f"🍴 Cloned {source_tile.name}'s upgrades to {target_tile.name}!"
        )

    async def _handle_event_force_buy(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        tile_id = payload.get("tile_id")

        if not tile_id:
            return ActionResult(success=False, message="Must specify a tile")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        tile = next((t for t in game.board if t.id == tile_id), None)
        if not tile:
            return ActionResult(success=False, message="Tile not found")

        if not tile.owner_id or tile.owner_id == player_id:
            return ActionResult(success=False, message="Property must be owned by another player")

        event_data = game.pending_decision.event_data if game.pending_decision else {}
        actions_data = (event_data.get("actions") or {}) if event_data else {}
        multiplier = actions_data.get("force_buy_multiplier", 1.5)
        cost = int(tile.price * multiplier)

        if player.cash < cost:
            return ActionResult(success=False, message=f"Insufficient funds (need ${cost})")

        old_owner = next((p for p in game.players if p.id == tile.owner_id), None)
        if old_owner:
            old_owner.cash += cost
            await self.repository.update_player_cash(old_owner.id, old_owner.cash)
            if tile.id in old_owner.properties:
                old_owner.properties = [p for p in old_owner.properties if p != tile.id]
                await self.repository.update_player_properties(old_owner.id, old_owner.properties)

        player.cash -= cost
        await self.repository.update_player_cash(player_id, player.cash)
        player.properties = list(player.properties) + [tile.id]
        await self.repository.update_player_properties(player.id, player.properties)

        tile.owner_id = player_id
        await self.repository.update_tile_owner(tile.id, player_id)

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        await self.repository.update(game)

        return ActionResult(
            success=True, message=f"⚔️ Hostile Takeover! Bought {tile.name} for ${cost}"
        )

    async def _handle_event_free_landing(
        self, game: GameSession, player_id: str, payload: dict[str, Any]
    ) -> ActionResult:
        tile_id = payload.get("tile_id")

        if not tile_id:
            return ActionResult(success=False, message="Must specify a tile")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        tile = next((t for t in game.board if t.id == tile_id), None)
        if not tile:
            return ActionResult(success=False, message="Tile not found")

        if tile.owner_id != player_id:
            return ActionResult(success=False, message="You must own the property")

        event_data = game.pending_decision.event_data if game.pending_decision else {}
        actions_data = (event_data.get("actions") or {}) if event_data else {}
        free_rounds = actions_data.get("free_rounds", 1)

        tile.free_landing_until_round = game.current_round + free_rounds
        await self.repository.save_board(game.id, game.board)

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        await self.repository.update(game)

        return ActionResult(
            success=True,
            message=f"🔓 Open Source! {tile.name} is free to land on for {free_rounds} round(s)",
        )

    async def _handle_tile_landing_callback(
        self, game: GameSession, player: "Player", tile: "Tile"
    ) -> None:
        pass

    async def _check_and_handle_end_conditions(self, game_id: str) -> bool:
        """Check for bankruptcy, FIRST_TO_CASH, and game end. Returns True if game ended."""
        from app.modules.sastadice.schemas import GameStatus, WinCondition

        game = await self._get_game(game_id)

        for player in game.players:
            if player.cash < 0 and not player.is_bankrupt:
                player.is_bankrupt = True
                await self.repository.update_player_bankrupt(player.id, True)

        active_players = [p for p in game.players if not p.is_bankrupt]

        if (
            game.settings.win_condition == WinCondition.FIRST_TO_CASH
            and game.settings.target_cash > 0
        ):
            richest = max(active_players, key=lambda p: p.cash)
            if richest.cash >= game.settings.target_cash:
                game = await self._get_game(game_id)
                game.status = GameStatus.FINISHED
                game.winner_id = richest.id
                game.last_event_message = (
                    f"💰 FIRST TO CASH! {richest.name} wins with ${richest.cash}!"
                )
                await self.repository.update(game)
                return True

        if len(active_players) <= 1:
            game = await self._get_game(game_id)
            game.status = GameStatus.FINISHED
            winner = (
                active_players[0] if active_players else max(game.players, key=lambda x: x.cash)
            )
            game.winner_id = winner.id
            game.last_event_message = f"🏆 GAME OVER! {winner.name} wins with ${winner.cash}!"
            await self.repository.update(game)
            return True

        return False

    def _determine_winner(self, game: GameSession) -> dict[str, Any] | None:
        return self.economy_manager.determine_winner(game)
