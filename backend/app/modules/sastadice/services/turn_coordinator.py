"""Turn coordination logic - dice rolling and turn advancement."""

import random
import time
from typing import TYPE_CHECKING, Optional

from app.modules.sastadice.schemas import (
    ActionResult,
    DiceRollResult,
    GameStatus,
    TurnPhase,
    WinCondition,
)

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import (
        GameSession,
        Player,
    )
    from app.modules.sastadice.services.turn_manager import TurnManager


class TurnCoordinator:
    """Coordinates dice rolling and turn advancement logic."""

    def __init__(
        self,
        repository: "GameRepository",
        turn_manager: "TurnManager",
    ) -> None:
        self.repository = repository
        self.turn_manager = turn_manager

    async def _validate_roll_dice(
        self, game: "GameSession", player_id: str
    ) -> tuple[bool, str | None, Optional["Player"]]:
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

    async def _handle_jail_roll(
        self, game: "GameSession", player: "Player", send_to_jail_callback
    ) -> DiceRollResult | None:
        player.jail_turns += 1
        if player.jail_turns >= 1:
            player.in_jail = False
            player.jail_turns = 0
            player.consecutive_doubles = 0
            game.last_event_message = f"✅ {player.name} released from SERVER DOWNTIME!"
            return None
        else:
            game.last_event_message = (
                f"⏳ {player.name} stuck in SERVER DOWNTIME. Wait or pay $50 bribe."
            )
            game.turn_phase = TurnPhase.POST_TURN
            await self.repository.update(game)
            return DiceRollResult(dice1=0, dice2=0, total=0, is_doubles=False)

    async def _execute_dice_roll(
        self, game: "GameSession", player: "Player", send_to_jail_callback
    ) -> tuple[int, int, int, bool, bool]:
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

    async def _handle_movement(
        self,
        game: "GameSession",
        player: "Player",
        player_id: str,
        total: int,
        stimulus_active: bool,
    ) -> bool:
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

    async def _finalize_roll(
        self,
        game: "GameSession",
        player: "Player",
        dice1: int,
        dice2: int,
        total: int,
        is_doubles: bool,
        passed_go: bool,
        stimulus_active: bool,
        handle_tile_landing_callback,
    ) -> DiceRollResult:
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

        landed_tile = game.board[player.position] if player.position < len(game.board) else None

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
        send_to_jail_callback,
        handle_tile_landing_callback,
    ) -> DiceRollResult:
        is_valid, error_msg, player = await self._validate_roll_dice(game, player_id)
        if not is_valid:
            raise ValueError(error_msg)

        if player.in_jail:
            result = await self._handle_jail_roll(game, player, send_to_jail_callback)
            if result is not None:
                return result

        dice1, dice2, total, is_doubles, went_to_jail = await self._execute_dice_roll(
            game, player, send_to_jail_callback
        )

        if went_to_jail:
            return DiceRollResult(dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles)

        stimulus_active = player.cash < 100
        passed_go = await self._handle_movement(game, player, player_id, total, stimulus_active)

        return await self._finalize_roll(
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

    async def _check_doubles_replay(
        self, game: "GameSession", player: "Player"
    ) -> ActionResult | None:
        if player and game.last_dice_roll and game.last_dice_roll.get("is_doubles"):
            game.turn_phase = TurnPhase.PRE_ROLL
            game.pending_decision = None
            game.last_dice_roll = None
            game.last_event_message = f"🎲 DOUBLES! {player.name} rolls again!"
            await self.repository.update(game)
            return ActionResult(success=True, message="Doubles! Roll again!")
        return None

    async def _check_game_end_conditions(
        self,
        game: "GameSession",
        check_end_conditions_callback,
        determine_winner_callback,
    ) -> ActionResult | None:
        if await check_end_conditions_callback(game.id):
            updated_game = await self.repository.get_by_id(game.id)
            if not updated_game:
                return ActionResult(success=False, message="Game not found")
            winner = determine_winner_callback(updated_game)
            if not winner:
                return ActionResult(success=False, message="Could not determine winner")
            return ActionResult(
                success=True,
                message=f"🏆 Game Over! {winner['name']} wins!",
                data={"game_over": True, "winner": winner},
            )
        return None

    async def _advance_to_next_player(self, game: "GameSession") -> tuple["Player", int]:
        active_players = [p for p in game.players if not p.is_bankrupt]
        current_index = next(
            (i for i, p in enumerate(active_players) if p.id == game.current_turn_player_id),
            0,
        )
        next_index = (current_index + 1) % len(active_players)
        next_player = active_players[next_index]

        if not game.first_player_id:
            game.first_player_id = active_players[0].id if active_players else None

        old_round = game.current_round
        return next_player, old_round

    async def _increment_round_if_needed(
        self,
        game: "GameSession",
        next_player: "Player",
        old_round: int,
        check_sudden_death_callback,
    ) -> ActionResult | None:
        if next_player.id == game.first_player_id:
            game.current_round += 1

            for tile in game.board:
                if tile.blocked_until_round and tile.blocked_until_round <= game.current_round:
                    tile.blocked_until_round = None

            sudden_death_result = await check_sudden_death_callback(game)
            if sudden_death_result:
                return sudden_death_result

        return None

    async def _check_sudden_death(
        self, game: "GameSession", determine_winner_callback
    ) -> ActionResult | None:
        if (
            game.settings.win_condition == WinCondition.SUDDEN_DEATH
            and game.settings.round_limit > 0
            and game.current_round >= game.settings.round_limit
        ):
            winner = determine_winner_callback(game)
            if not winner:
                return ActionResult(success=False, message="Could not determine winner")
            game.status = GameStatus.FINISHED
            await self.repository.save_board(game.id, game.board)
            await self.repository.update(game)
            return ActionResult(
                success=True,
                message=f"⏰ ROUND {game.settings.round_limit}! SUDDEN DEATH! {winner['name']} wins with ${winner['cash']}!",
                data={"game_over": True, "winner": winner, "sudden_death": True},
            )
        return None

    async def handle_end_turn(
        self,
        game: "GameSession",
        player_id: str,
        check_end_conditions_callback,
        determine_winner_callback,
    ) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        if game.turn_phase != TurnPhase.POST_TURN:
            return ActionResult(
                success=False,
                message=f"Cannot end turn in {game.turn_phase.value} phase",
            )

        player = next((p for p in game.players if p.id == player_id), None)

        doubles_result = await self._check_doubles_replay(game, player)
        if doubles_result:
            return doubles_result

        end_result = await self._check_game_end_conditions(
            game, check_end_conditions_callback, determine_winner_callback
        )
        if end_result:
            return end_result

        updated_game = await self.repository.get_by_id(game.id)
        if not updated_game:
            return ActionResult(success=False, message="Game not found")

        next_player, old_round = await self._advance_to_next_player(updated_game)

        async def check_sudden_death(g: "GameSession") -> ActionResult | None:
            return await self._check_sudden_death(g, determine_winner_callback)

        sudden_death_result = await self._increment_round_if_needed(
            updated_game, next_player, old_round, check_sudden_death
        )
        if sudden_death_result:
            return sudden_death_result

        updated_game.current_turn_player_id = next_player.id
        updated_game.turn_phase = TurnPhase.PRE_ROLL
        updated_game.pending_decision = None
        updated_game.last_dice_roll = None
        updated_game.last_event_message = None
        updated_game.turn_start_time = time.time()

        if updated_game.current_round > old_round:
            await self.repository.save_board(updated_game.id, updated_game.board)

        await self.repository.update(updated_game)

        round_limit_display = (
            updated_game.settings.round_limit if updated_game.settings.round_limit > 0 else "∞"
        )
        round_info = f" [Round {updated_game.current_round}/{round_limit_display}]"
        return ActionResult(
            success=True, message=f"Turn ended. {next_player.name}'s turn!{round_info}"
        )
