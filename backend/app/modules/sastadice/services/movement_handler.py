"""Movement handler - dice rolling and player movement."""
import random
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession, Player
    from app.modules.sastadice.services.turn_manager import TurnManager

from app.modules.sastadice.schemas import DiceRollResult, GameStatus, TurnPhase


class MovementHandler:
    """Handles dice rolling, movement, and GO passing."""

    def __init__(
        self,
        repository: "GameRepository",
        turn_manager: "TurnManager",
    ) -> None:
        """Initialize movement handler."""
        self.repository = repository
        self.turn_manager = turn_manager

    async def validate_roll_dice(
        self, game: "GameSession", player_id: str
    ) -> tuple[bool, str | None, "Player | None"]:
        """Validate dice roll action."""
        if game.status != GameStatus.ACTIVE:
            return False, "Game must be ACTIVE to roll dice", None

        if game.current_turn_player_id != player_id:
            return False, "Not your turn", None

        if game.turn_phase != TurnPhase.PRE_ROLL:
            return False, "Cannot roll dice in current turn phase", None

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "Player not found", None

        return True, None, player

    async def execute_dice_roll(
        self, game: "GameSession", player: "Player", send_to_jail_callback: Callable
    ) -> tuple[int, int, int, bool, bool]:
        """Execute dice roll with stimulus check."""
        stimulus_active = player.cash < 100
        if stimulus_active:
            dice_rolls = sorted([random.randint(1, 6) for _ in range(3)], reverse=True)
            dice1, dice2 = dice_rolls[0], dice_rolls[1]
            game.last_event_message = "💰 STIMULUS CHECK! Roll 3, keep best 2!"
        else:
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)

        total = dice1 + dice2
        is_doubles = dice1 == dice2

        if is_doubles:
            player.consecutive_doubles += 1
            if player.consecutive_doubles >= 3:
                await send_to_jail_callback(game, player)
                player.consecutive_doubles = 0
                game.turn_phase = TurnPhase.POST_TURN
                game.last_dice_roll = {
                    "dice1": dice1,
                    "dice2": dice2,
                    "total": total,
                    "is_doubles": is_doubles,
                    "passed_go": False,
                    "went_to_jail": True,
                }
                await self.repository.update(game)
                return dice1, dice2, total, is_doubles, True
        else:
            player.consecutive_doubles = 0

        return dice1, dice2, total, is_doubles, False

    async def handle_movement(
        self,
        game: "GameSession",
        player: "Player",
        player_id: str,
        total: int,
        stimulus_active: bool,
    ) -> bool:
        """Handle player movement and GO passing."""
        old_position = player.position
        new_position = (player.position + total) % len(game.board)
        passed_go = new_position < old_position and old_position != 0

        if passed_go:
            go_bonus = self.turn_manager.calculate_go_bonus(game)
            new_cash = player.cash + go_bonus
            await self.repository.update_player_cash(player_id, new_cash)
            player.cash = new_cash
            if not stimulus_active:
                game.last_event_message = f"🚀 Passed GO! Collected ${go_bonus}"

        await self.repository.update_player_position(player_id, new_position)
        player.position = new_position
        return passed_go

    async def finalize_roll(
        self,
        game: "GameSession",
        player: "Player",
        dice1: int,
        dice2: int,
        total: int,
        is_doubles: bool,
        passed_go: bool,
        stimulus_active: bool,
        handle_tile_landing_callback: Callable,
    ) -> DiceRollResult:
        """Finalize dice roll and trigger tile landing."""
        game.last_dice_roll = {
            "dice1": dice1,
            "dice2": dice2,
            "total": total,
            "is_doubles": is_doubles,
            "passed_go": passed_go,
            "stimulus_check": stimulus_active,
        }

        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = None
        if not stimulus_active and not passed_go:
            game.last_event_message = None

        landed_tile = (
            game.board[player.position] if player.position < len(game.board) else None
        )

        if landed_tile:
            await handle_tile_landing_callback(game, player, landed_tile)

        if game.turn_phase == TurnPhase.DECISION and not game.pending_decision:
            game.turn_phase = TurnPhase.POST_TURN

        await self.repository.update(game)

        return DiceRollResult(dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles)

    async def roll_dice(
        self,
        game: "GameSession",
        player_id: str,
        send_to_jail_callback: Callable,
        handle_tile_landing_callback: Callable,
    ) -> DiceRollResult:
        """Roll dice for a player - main entry point."""
        is_valid, error_msg, player = await self.validate_roll_dice(game, player_id)
        if not is_valid:
            raise ValueError(error_msg)

        if player.in_jail:
            from app.modules.sastadice.services.jail_manager import JailManager

            escaped, dice1, dice2, message = JailManager.roll_for_doubles(game, player)
            if not escaped:
                game.last_event_message = message
                game.turn_phase = TurnPhase.POST_TURN
                await self.repository.update(game)
                return DiceRollResult(dice1=dice1, dice2=dice2, total=dice1 + dice2, is_doubles=dice1 == dice2)
            else:
                game.last_event_message = message
                await self.repository.update(game)

        dice1, dice2, total, is_doubles, went_to_jail = await self.execute_dice_roll(
            game, player, send_to_jail_callback
        )

        if went_to_jail:
            return DiceRollResult(
                dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles
            )

        stimulus_active = player.cash < 100
        passed_go = await self.handle_movement(game, player, player_id, total, stimulus_active)

        return await self.finalize_roll(
            game,
            player,
            dice1,
            dice2,
            total,
            is_doubles,
            passed_go,
            stimulus_active,
            handle_tile_landing_callback,
        )
