"""CPU turn executor - state machine for executing CPU turns."""
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import ActionType, TurnPhase

from app.modules.sastadice.services.cpu_strategy import CpuStrategy


class CpuTurnState(str, Enum):
    """CPU turn state machine states."""

    PRE_ROLL = "PRE_ROLL"
    MOVING = "MOVING"
    DECISION = "DECISION"
    POST_TURN = "POST_TURN"
    AUCTION = "AUCTION"
    COMPLETE = "COMPLETE"


class CpuTurnExecutor:
    """Executes CPU turns using state machine pattern."""

    def __init__(self, orchestrator: Any, strategy: CpuStrategy) -> None:
        """Initialize with orchestrator and strategy."""
        self.orchestrator = orchestrator
        self.strategy = strategy

    async def play_cpu_turn(
        self, game: "GameSession", cpu_player: "Player"
    ) -> list[str]:
        """Play a full CPU turn using state machine pattern."""
        turn_log = []
        max_iterations = 20
        iterations = 0

        state = CpuTurnState(game.turn_phase.value)

        handlers = {
            CpuTurnState.PRE_ROLL: lambda g, p: self._handle_cpu_pre_roll(g, p),
            CpuTurnState.MOVING: lambda g, p: self._handle_cpu_moving(g, p),
            CpuTurnState.DECISION: lambda g, p: self._handle_cpu_decision(g, p),
            CpuTurnState.POST_TURN: lambda g, p: self._handle_cpu_post_turn(g, p),
            CpuTurnState.AUCTION: lambda g, p: self._handle_cpu_auction(g, p),
        }

        while iterations < max_iterations:
            iterations += 1
            game = await self.orchestrator.get_game(game.id)

            if game.current_turn_player_id != cpu_player.id:
                turn_log.append(
                    f"{cpu_player.name} turn ended (not their turn anymore)"
                )
                break

            cpu_player = next(
                (p for p in game.players if p.id == cpu_player.id), cpu_player
            )
            if not cpu_player:
                turn_log.append(f"{cpu_player.name} not found in game")
                break

            handler = handlers.get(state)
            if not handler:
                turn_log.append(
                    f"{cpu_player.name} stuck in unexpected phase: {state.value}"
                )
                break

            new_state, log_entry = await handler(game, cpu_player)
            if log_entry:
                turn_log.append(log_entry)

            if new_state == CpuTurnState.COMPLETE:
                break

            state = new_state

        if iterations >= max_iterations:
            turn_log.append(
                f"{cpu_player.name} hit max iterations limit ({max_iterations})"
            )

        return turn_log

    async def _handle_cpu_pre_roll(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, str | None]:
        """Handle CPU pre-roll phase."""
        roll_result = await self.orchestrator.perform_action(
            game.id, cpu_player.id, ActionType.ROLL_DICE, {}
        )
        if roll_result.success:
            updated_game = await self.orchestrator.get_game(game.id)
            new_state = CpuTurnState(updated_game.turn_phase.value)
            return new_state, f"{cpu_player.name} rolled: {roll_result.message}"
        else:
            return (
                CpuTurnState.COMPLETE,
                f"{cpu_player.name} failed to roll: {roll_result.message}",
            )

    async def _handle_cpu_decision(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, str | None]:
        """Handle CPU decision phase."""
        if not game.pending_decision:
            game = await self.orchestrator.get_game(game.id)
            game.turn_phase = TurnPhase.POST_TURN
            game.pending_decision = None
            await self.orchestrator.repository.update(game)
            return (
                CpuTurnState.POST_TURN,
                f"{cpu_player.name} in DECISION phase but no pending decision - transitioning to POST_TURN",
            )

        decision_type = game.pending_decision.type
        if decision_type == "BUY":
            if self.strategy.should_buy_property(
                cpu_player, game.pending_decision.price
            ):
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.BUY_PROPERTY, {}
                )
                updated_game = await self.orchestrator.get_game(game.id)
                if result.success:
                    return (
                        CpuTurnState(updated_game.turn_phase.value),
                        f"{cpu_player.name} bought property: {result.message}",
                    )
                else:
                    result = await self.orchestrator.perform_action(
                        game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
                    )
                    updated_game = await self.orchestrator.get_game(game.id)
                    return (
                        CpuTurnState(updated_game.turn_phase.value),
                        f"{cpu_player.name} passed (buy failed: {result.message})",
                    )
            else:
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
                )
                updated_game = await self.orchestrator.get_game(game.id)
                return (
                    CpuTurnState(updated_game.turn_phase.value),
                    f"{cpu_player.name} passed on property (insufficient funds)",
                )
        elif decision_type in ("MARKET", "BLACK_MARKET"):
            result = await self.orchestrator.perform_action(
                game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
            )
            updated_game = await self.orchestrator.get_game(game.id)
            return (
                CpuTurnState(updated_game.turn_phase.value),
                f"{cpu_player.name} left Black Market",
            )
        else:
            result = await self.orchestrator.perform_action(
                game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
            )
            updated_game = await self.orchestrator.get_game(game.id)
            return (
                CpuTurnState(updated_game.turn_phase.value),
                f"{cpu_player.name} passed on decision type: {decision_type}",
            )

    async def _handle_cpu_post_turn(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, str | None]:
        """Handle CPU post-turn phase."""
        turn_manager = self.orchestrator.turn_manager
        upgraded = await self._try_upgrade_properties(game, cpu_player, turn_manager)
        if upgraded:
            game = await self.orchestrator.get_game(game.id)
            cpu_player = next(
                (p for p in game.players if p.id == cpu_player.id), cpu_player
            )
            return CpuTurnState.POST_TURN, f"{cpu_player.name} upgraded a property"

        result = await self.orchestrator.perform_action(
            game.id, cpu_player.id, ActionType.END_TURN, {}
        )
        if result.success:
            return CpuTurnState.COMPLETE, f"{cpu_player.name} ended turn"
        else:
            return (
                CpuTurnState.COMPLETE,
                f"{cpu_player.name} failed to end turn: {result.message}",
            )

    async def _try_upgrade_properties(
        self, game: "GameSession", cpu_player: "Player", turn_manager
    ) -> bool:
        """Try to upgrade properties using strategy."""
        from app.modules.sastadice.schemas import TileType

        for tile in game.board:
            if tile.owner_id != cpu_player.id or tile.type != TileType.PROPERTY:
                continue
            if tile.upgrade_level >= 2:
                continue
            if not tile.color or not turn_manager.owns_full_set(
                cpu_player, tile.color, game.board
            ):
                continue

            upgrade_cost = self.strategy.calculate_upgrade_cost(tile)
            if self.strategy.should_upgrade_property(cpu_player, tile, upgrade_cost):
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.UPGRADE, {"tile_id": tile.id}
                )
                if result.success:
                    return True
        return False

    async def _handle_cpu_moving(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, str | None]:
        """Handle CPU moving phase - just wait for transition."""
        updated_game = await self.orchestrator.get_game(game.id)
        new_state = CpuTurnState(updated_game.turn_phase.value)
        return new_state, None

    async def _handle_cpu_auction(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, str | None]:
        """Handle CPU auction phase."""
        return (
            CpuTurnState.AUCTION,
            f"{cpu_player.name} pausing turn for Auction",
        )
