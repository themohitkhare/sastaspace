"""Lobby manager for game setup and player management."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.services.board_generation_service import BoardGenerationService
    from app.modules.sastadice.services.turn_manager import TurnManager

from app.modules.sastadice.schemas import (
    GameSession,
    GameSettings,
    GameStatus,
    Player,
    PlayerCreate,
    Tile,
    TileCreate,
    TurnPhase,
)


class LobbyManager:
    """Handles game creation, joining, ready toggling, and settings."""

    def __init__(
        self,
        repository: "GameRepository",
        board_service: "BoardGenerationService",
        turn_manager: "TurnManager",
    ) -> None:
        """Initialize lobby manager with dependencies."""
        self.repository = repository
        self.board_service = board_service
        self.turn_manager = turn_manager

    async def get_game(self, game_id: str) -> GameSession:
        """Get game session by ID."""
        game = await self.repository.get_by_id(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        return game

    async def create_game(self, cpu_count: int = 0) -> GameSession:
        """Create a new game session with optional CPU players."""
        game = await self.repository.create_game()

        if cpu_count > 0:
            await self.add_cpu_players_to_game(game.id, cpu_count)
            game = await self.get_game(game.id)

        return game

    async def add_cpu_players_to_game(self, game_id: str, count: int) -> None:
        """Add a specific number of CPU players to the game (auto-ready)."""
        game = await self.get_game(game_id)
        cpu_names = ["ROBOCOP", "CHAD BOT", "KAREN.EXE", "STONKS", "CPU-5"]

        for i in range(min(count, 5)):
            cpu_name = cpu_names[i]
            tiles = self.board_service.generate_seeded_tiles_for_player(
                cpu_name, game.players
            )
            player_create = PlayerCreate(name=cpu_name)
            player = await self.repository.add_player(game_id, player_create)
            await self.repository.submit_tiles(game_id, player.id, tiles)
            await self.repository.toggle_player_ready(player.id)
            game = await self.get_game(game_id)

    async def update_settings(
        self, game_id: str, host_id: str, settings_dict: dict
    ) -> dict:
        """Update game settings. Only host can update."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot change settings after game has started")

        if game.host_id != host_id:
            raise ValueError("Only the host can change game settings")

        new_settings = GameSettings(**{**game.settings.model_dump(), **settings_dict})
        game.settings = new_settings
        game.max_rounds = new_settings.round_limit

        await self.repository.update(game)

        return {"updated": True, "settings": new_settings.model_dump()}

    async def join_game(
        self, game_id: str, player_name: str, tiles: list[TileCreate] | None = None
    ) -> Player:
        """Join a game and submit tiles (or use seeded tiles if not provided)."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot join game that is not in LOBBY status")

        if tiles is None:
            tiles = self.board_service.generate_seeded_tiles_for_player(
                player_name, game.players
            )
        elif len(tiles) != 5:
            raise ValueError("Must submit exactly 5 tiles")

        is_first_player = len(game.players) == 0

        player_create = PlayerCreate(name=player_name)
        player = await self.repository.add_player(game_id, player_create)
        await self.repository.submit_tiles(game_id, player.id, tiles)

        if is_first_player or game.host_id is None:
            await self.repository.set_host(game_id, player.id)

        game = await self.get_game(game_id)
        await self.repository.update(game)

        game = await self.get_game(game_id)
        player = next((p for p in game.players if p.id == player.id), player)
        player.submitted_tiles = tiles

        return player

    async def kick_player(
        self, game_id: str, host_id: str, target_player_id: str
    ) -> dict:
        """Kick a player from the game. Only host can kick."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot kick players after game has started")

        if game.host_id != host_id:
            raise ValueError("Only the host can kick players")

        if target_player_id == host_id:
            raise ValueError("Cannot kick yourself")

        target_player = next(
            (p for p in game.players if p.id == target_player_id), None
        )
        if not target_player:
            raise ValueError("Player not found in this game")

        await self.repository.remove_player(game_id, target_player_id)

        return {
            "kicked": True,
            "player_id": target_player_id,
            "player_name": target_player.name,
        }

    async def add_cpu_players(self, game_id: str, target_count: int = 2) -> None:
        """Add CPU players to reach target count (auto-ready)."""
        game = await self.get_game(game_id)
        current_count = len(game.players)

        if current_count >= target_count:
            return

        cpu_names = ["ROBOCOP", "CHAD BOT", "KAREN.EXE", "STONKS", "CPU-5"]

        for i in range(target_count - current_count):
            cpu_name = cpu_names[min(i, len(cpu_names) - 1)]
            if i >= len(cpu_names):
                cpu_name = f"CPU-{i + 1}"

            tiles = self.board_service.generate_seeded_tiles_for_player(
                cpu_name, game.players
            )

            player_create = PlayerCreate(name=cpu_name)
            player = await self.repository.add_player(game_id, player_create)
            await self.repository.submit_tiles(game_id, player.id, tiles)
            await self.repository.toggle_player_ready(player.id)

            game = await self.get_game(game_id)
            await self.repository.update(game)

    async def toggle_ready(self, game_id: str, player_id: str) -> dict:
        """Toggle player's launch key. Auto-starts if all players ready."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game already started")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise ValueError("Player not in this game")

        new_ready = await self.repository.toggle_player_ready(player_id)
        await self.repository.update(game)  # Bump version for polling

        all_ready = await self.repository.are_all_players_ready(game_id)
        game_started = False

        if all_ready and len(game.players) >= 1:
            game_started = True

        return {
            "player_id": player_id,
            "ready": new_ready,
            "all_ready": all_ready,
            "game_started": game_started,
        }

    async def start_game(self, game_id: str, force: bool = False) -> GameSession:
        """Start a game and generate the board."""
        import time
        from app.modules.sastadice.services.board_generation_service import GameConfig

        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game must be in LOBBY status to start")

        if not force and not await self.repository.are_all_players_ready(game_id):
            raise ValueError("All players must turn their launch keys")

        if len(game.players) < 2:
            await self.add_cpu_players(game_id, target_count=2)
            game = await self.get_game(game_id)

        all_player_tiles = []
        for player in game.players:
            for tile_create in player.submitted_tiles:
                tile = Tile(
                    type=tile_create.type,
                    name=tile_create.name,
                    effect_config=tile_create.effect_config,
                )
                all_player_tiles.append(tile)

        board_size, _, padding = self.board_service.calculate_dimensions(
            len(game.players)
        )

        min_tiles_for_good_game = max(20, board_size * 4 - 4)
        player_tile_count = len(all_player_tiles)
        additional_tiles_needed = max(0, min_tiles_for_good_game - player_tile_count)

        if additional_tiles_needed > 0:
            generated_tiles = self.board_service.generate_additional_tiles(
                additional_tiles_needed, all_player_tiles
            )
            all_player_tiles.extend(generated_tiles)
            padding = max(0, padding - additional_tiles_needed)

        total_tiles = len(all_player_tiles) + padding + 1
        game_config = GameConfig(total_tiles, len(game.players))

        board = self.board_service.generate_board(
            all_player_tiles, board_size, padding, game_config
        )

        await self.repository.save_board(game_id, board)
        await self.repository.set_players_starting_cash(
            game_id, game_config.starting_cash
        )

        game.status = GameStatus.ACTIVE
        game.turn_phase = TurnPhase.PRE_ROLL
        game.board = board
        game.board_size = board_size
        game.current_turn_player_id = game.players[0].id if game.players else None
        game.starting_cash = game_config.starting_cash
        game.go_bonus = game_config.go_bonus
        game.turn_start_time = time.time()

        from app.modules.sastadice.events.event_manager import EventManager
        EventManager.initialize_deck(game)

        await self.repository.update(game)
        return await self.get_game(game_id)
