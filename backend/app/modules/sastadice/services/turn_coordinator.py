"""Turn coordinator - backward compatibility wrapper."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.schemas import GameSession
    from app.modules.sastadice.services.turn_manager import TurnManager

from app.modules.sastadice.schemas import ActionResult, DiceRollResult
from app.modules.sastadice.services.movement_handler import MovementHandler
from app.modules.sastadice.services.turn_advancement_handler import TurnAdvancementHandler


class TurnCoordinator:
    """Coordinates dice rolling and turn advancement - backward compatibility wrapper."""

    def __init__(
        self,
        repository: "GameRepository",
        turn_manager: "TurnManager",
    ) -> None:
        """Initialize turn coordinator."""
        self.repository = repository
        self.turn_manager = turn_manager
        self.movement_handler = MovementHandler(repository, turn_manager)
        self.advancement_handler = TurnAdvancementHandler(repository)

    async def roll_dice(
        self,
        game: "GameSession",
        player_id: str,
        send_to_jail_callback: Callable[..., Awaitable[None]],
        handle_tile_landing_callback: Callable[..., Awaitable[None]],
    ) -> DiceRollResult:
        """Roll dice for a player."""
        return await self.movement_handler.roll_dice(
            game, player_id, send_to_jail_callback, handle_tile_landing_callback
        )

    async def handle_end_turn(
        self,
        game: "GameSession",
        player_id: str,
        check_end_conditions_callback: Callable[..., Awaitable[bool]],
        determine_winner_callback: Callable[..., Awaitable[dict[str, Any] | None]],
    ) -> ActionResult:
        """Handle end turn action."""
        return await self.advancement_handler.handle_end_turn(
            game,
            player_id,
            check_end_conditions_callback,
            determine_winner_callback,
        )
