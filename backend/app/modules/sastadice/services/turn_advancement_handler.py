"""Turn advancement handler - end turn and round management."""

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import ActionResult, GameStatus, TurnPhase, WinCondition


class TurnAdvancementHandler:
    """Handles turn advancement and round management."""

    def __init__(self, repository: "GameRepository") -> None:
        self.repository = repository

    async def handle_end_turn(
        self,
        game: "GameSession",
        player_id: str,
        check_end_conditions_callback: Callable[..., Awaitable[bool]],
        determine_winner_callback: Callable[..., Awaitable[dict[str, Any] | None]],
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
        next_player = await self._skip_players_with_skip_turn(updated_game, next_player)

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

    async def _check_doubles_replay(
        self, game: "GameSession", player: "Player | None"
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
        check_end_conditions_callback: Callable[..., Awaitable[bool]],
        determine_winner_callback: Callable[..., Awaitable[dict[str, Any] | None]],
    ) -> ActionResult | None:
        if await check_end_conditions_callback(game.id):
            updated_game = await self.repository.get_by_id(game.id)
            if not updated_game:
                return ActionResult(success=False, message="Game not found")
            winner: dict[str, Any] | None = await determine_winner_callback(updated_game)
            if not winner:
                return ActionResult(success=False, message="Could not determine winner")
            return ActionResult(
                success=True,
                message=f"🏆 Game Over! {winner['name']} wins!",
                data={"game_over": True, "winner": winner},
            )
        return None

    async def _skip_players_with_skip_turn(
        self, game: "GameSession", start_player: "Player"
    ) -> "Player":
        """Skip players who have SKIP_TURN buff until we find one who doesn't."""
        active_players = [p for p in game.players if not p.is_bankrupt]
        if not active_players:
            return start_player
        current_index = next(
            (i for i, p in enumerate(active_players) if p.id == start_player.id),
            0,
        )
        seen = set()
        while start_player.active_buff == "SKIP_TURN":
            if start_player.id in seen:
                break
            seen.add(start_player.id)
            start_player.active_buff = None
            await self.repository.update_player_buff(start_player.id, None)
            game.last_event_message = f"⏭️ {start_player.name} skipped turn (Coffee Break)!"
            current_index = (current_index + 1) % len(active_players)
            start_player = active_players[current_index]
        return start_player

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
        check_sudden_death_callback: Callable[..., Awaitable[ActionResult | None]],
    ) -> ActionResult | None:
        if next_player.id == game.first_player_id:
            game.current_round += 1
            game.rent_multiplier = 1.0
            game.go_bonus_multiplier = 1.0

            for tile in game.board:
                if tile.blocked_until_round and tile.blocked_until_round <= game.current_round:
                    tile.blocked_until_round = None

            sudden_death_result = await check_sudden_death_callback(game)
            if sudden_death_result:
                return sudden_death_result

        return None

    async def _check_sudden_death(
        self,
        game: "GameSession",
        determine_winner_callback: Callable[..., Awaitable[dict[str, Any] | None]],
    ) -> ActionResult | None:
        if (
            game.settings.win_condition == WinCondition.SUDDEN_DEATH
            and game.settings.round_limit > 0
            and game.current_round >= game.settings.round_limit
        ):
            winner: dict[str, Any] | None = await determine_winner_callback(game)
            if not winner:
                return ActionResult(success=False, message="Could not determine winner")
            game.status = GameStatus.FINISHED
            game.winner_id = winner.get("id")
            await self.repository.save_board(game.id, game.board)
            await self.repository.update(game)
            return ActionResult(
                success=True,
                message=f"⏰ ROUND {game.settings.round_limit}! SUDDEN DEATH! {winner['name']} wins with ${winner['cash']}!",
                data={"game_over": True, "winner": winner, "sudden_death": True},
            )
        return None
