"""CPU manager - thin wrapper coordinating strategy and executor."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import ActionType, GameStatus, TileType
from app.modules.sastadice.services.cpu_strategy import CpuStrategy
from app.modules.sastadice.services.cpu_turn_executor import CpuTurnExecutor

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
        self.orchestrator = orchestrator
        self.strategy = CpuStrategy()
        self.executor = CpuTurnExecutor(orchestrator, self.strategy)

    @staticmethod
    def is_cpu_player(player: "Player") -> bool:
        return player.name in CPU_NAMES

    async def cpu_upgrade_properties(
        self,
        game: "GameSession",
        cpu_player: "Player",
        turn_manager: Any,
    ) -> bool:
        for tile in game.board:
            if tile.owner_id != cpu_player.id or tile.type != TileType.PROPERTY:
                continue
            if tile.upgrade_level >= 2:
                continue
            if not tile.color or not turn_manager.owns_full_set(cpu_player, tile.color, game.board):
                continue

            upgrade_cost = self.strategy.calculate_upgrade_cost(tile)
            if self.strategy.should_upgrade_property(cpu_player, tile, upgrade_cost):
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.UPGRADE, {"tile_id": tile.id}
                )
                if result.success:
                    return True
        return False

    async def play_cpu_turn(self, game: "GameSession", cpu_player: "Player") -> list[str]:
        return await self.executor.play_cpu_turn(game, cpu_player)

    async def process_cpu_turns(self, game_id: str) -> dict[str, Any]:
        game = await self.orchestrator.get_game(game_id)
        all_logs = []
        max_cpu_turns = 10
        turns_played = 0

        while game.status == GameStatus.ACTIVE and turns_played < max_cpu_turns:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player or (
                not self.is_cpu_player(current_player)
                and not getattr(current_player, "disconnected", False)
            ):
                break

            turn_log = await self.play_cpu_turn(game, current_player)
            all_logs.extend(turn_log)
            turns_played += 1
            game = await self.orchestrator.get_game(game_id)

            if getattr(current_player, "disconnected", False):
                game = await self.orchestrator.get_game(game_id)
                disconnected_player = next(
                    (p for p in game.players if p.id == current_player.id),
                    current_player,
                )
                disconnected_turns = getattr(disconnected_player, "disconnected_turns", 0) + 1
                await self.orchestrator.repository.update_player_afk(
                    current_player.id,
                    getattr(disconnected_player, "afk_turns", 0),
                    True,
                    disconnected_turns=disconnected_turns,
                )
                if disconnected_turns >= 3:
                    from app.modules.sastadice.services.economy_manager import EconomyManager

                    game = await self.orchestrator.get_game(game_id)
                    current_player = next(
                        (p for p in game.players if p.id == current_player.id),
                        current_player,
                    )
                    econ = EconomyManager(self.orchestrator.repository)
                    await econ.process_bankruptcy(game, current_player, None)
                    await self.orchestrator.repository.update(game)
                    all_logs.append(f"{current_player.name} AFK Ghost → BANKRUPT after 3 turns!")
                    break

        return {"cpu_turns_played": turns_played, "log": all_logs}
