"""CPU manager - thin wrapper coordinating strategy and executor."""
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import ActionType, GameStatus

from app.modules.sastadice.services.cpu_strategy import CpuStrategy
from app.modules.sastadice.services.cpu_turn_executor import CpuTurnExecutor, CpuTurnState

CPU_NAMES = {
    "ROBOCOP",
    "CHAD BOT",
    "KAREN.EXE",
    "STONKS",
    "CPU-1",
    "CPU-2",
    "CPU-3",
    "CPU-4",
    "CPU-5",
}


class CpuManager:
    """AI logic for CPU players - coordinates strategy and executor."""

    CPU_NAMES = CPU_NAMES

    def __init__(self, orchestrator: Any) -> None:
        """Initialize with orchestrator."""
        self.orchestrator = orchestrator
        self.strategy = CpuStrategy()
        self.executor = CpuTurnExecutor(orchestrator, self.strategy)

    @staticmethod
    def is_cpu_player(player: "Player") -> bool:
        """Check if a player is a CPU."""
        return player.name in CPU_NAMES

    async def cpu_upgrade_properties(
        self, game: "GameSession", cpu_player: "Player", turn_manager
    ) -> bool:
        """CPU attempts to upgrade properties if beneficial. Returns True if upgraded."""
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

    async def play_cpu_turn(
        self, game: "GameSession", cpu_player: "Player"
    ) -> list[str]:
        """Play a full CPU turn using executor."""
        return await self.executor.play_cpu_turn(game, cpu_player)

    async def process_cpu_turns(self, game_id: str) -> dict:
        """Process all consecutive CPU turns until a human player's turn."""
        game = await self.orchestrator.get_game(game_id)
        all_logs = []
        max_cpu_turns = 10
        turns_played = 0

        while game.status == GameStatus.ACTIVE and turns_played < max_cpu_turns:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player or not self.is_cpu_player(current_player):
                break

            turn_log = await self.play_cpu_turn(game, current_player)
            all_logs.extend(turn_log)
            turns_played += 1
            game = await self.orchestrator.get_game(game_id)

        return {"cpu_turns_played": turns_played, "log": all_logs}
