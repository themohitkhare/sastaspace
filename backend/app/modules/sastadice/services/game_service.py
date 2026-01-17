"""Game service for managing game sessions and actions."""
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.services.board_generation_service import BoardGenerationService
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    Player,
    PlayerCreate,
    TileCreate,
    Tile,
    DiceRollResult,
    ActionType,
    ActionResult,
)


class GameService:
    """Service for game session management and actions."""

    def __init__(self, cursor) -> None:  # type: ignore
        """Initialize game service with database cursor."""
        self.repository = GameRepository(cursor)
        self.board_service = BoardGenerationService()

    def create_game(self) -> GameSession:
        """Create a new game session."""
        return self.repository.create_game()

    def get_game(self, game_id: str) -> GameSession:
        """Get game session by ID."""
        game = self.repository.get_by_id(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        return game

    def join_game(
        self, game_id: str, player_name: str, tiles: Optional[list[TileCreate]] = None
    ) -> Player:
        """Join a game and submit tiles (or use seeded tiles if not provided)."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot join game that is not in LOBBY status")

        if tiles is None:
            tiles = self.board_service.generate_seeded_tiles_for_player(
                player_name, game.players
            )
        elif len(tiles) != 5:
            raise ValueError("Must submit exactly 5 tiles")

        player_create = PlayerCreate(name=player_name)
        player = self.repository.add_player(game_id, player_create)
        self.repository.submit_tiles(game_id, player.id, tiles)

        game = self.get_game(game_id)
        self.repository.update(game)

        game = self.get_game(game_id)
        player = next((p for p in game.players if p.id == player.id), player)
        player.submitted_tiles = tiles

        return player

    def add_cpu_players(self, game_id: str, target_count: int = 2) -> None:
        """Add CPU players to reach target count."""
        game = self.get_game(game_id)
        current_count = len(game.players)
        
        if current_count >= target_count:
            return
        
        cpu_names = ["CPU-1", "CPU-2", "CPU-3", "CPU-4", "CPU-5"]
        
        for i in range(target_count - current_count):
            cpu_name = cpu_names[min(i, len(cpu_names) - 1)]
            if i >= len(cpu_names):
                cpu_name = f"CPU-{i + 1}"
            
            tiles = self.board_service.generate_seeded_tiles_for_player(
                cpu_name, game.players
            )
            
            player_create = PlayerCreate(name=cpu_name)
            player = self.repository.add_player(game_id, player_create)
            self.repository.submit_tiles(game_id, player.id, tiles)
            
            game = self.get_game(game_id)
            self.repository.update(game)

    def start_game(self, game_id: str) -> GameSession:
        """Start a game and generate the board."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game must be in LOBBY status to start")

        if len(game.players) < 2:
            self.add_cpu_players(game_id, target_count=2)
            game = self.get_game(game_id)

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

        board = self.board_service.generate_board(
            all_player_tiles, board_size, padding
        )

        self.repository.save_board(game_id, board)

        game.status = GameStatus.ACTIVE
        game.board = board
        game.board_size = board_size
        game.current_turn_player_id = game.players[0].id if game.players else None

        self.repository.update(game)

        return game

    def roll_dice(self, game_id: str, player_id: str) -> DiceRollResult:
        """Roll dice for a player."""
        game = self.get_game(game_id)

        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game must be ACTIVE to roll dice")

        if game.current_turn_player_id != player_id:
            raise ValueError("Not your turn")

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        is_doubles = dice1 == dice2

        player = next((p for p in game.players if p.id == player_id), None)
        if player:
            new_position = (player.position + total) % len(game.board)
            self.repository.update_player_position(player_id, new_position)

        self.repository.update(game)

        return DiceRollResult(
            dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles
        )

    def perform_action(
        self, game_id: str, player_id: str, action_type: ActionType, payload: dict
    ) -> ActionResult:
        """Perform a game action."""
        game = self.get_game(game_id)

        if action_type == ActionType.ROLL_DICE:
            dice_result = self.roll_dice(game_id, player_id)
            return ActionResult(
                success=True, message="Dice rolled", data=dice_result.model_dump()
            )

        elif action_type == ActionType.END_TURN:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Not your turn")

            current_index = next(
                (
                    i
                    for i, p in enumerate(game.players)
                    if p.id == game.current_turn_player_id
                ),
                0,
            )
            next_index = (current_index + 1) % len(game.players)
            game.current_turn_player_id = game.players[next_index].id

            self.repository.update(game)

            return ActionResult(success=True, message="Turn ended")

        elif action_type == ActionType.BUY_PROPERTY:
            return ActionResult(
                success=False, message="Buy property not yet implemented"
            )

        else:
            return ActionResult(success=False, message=f"Unknown action: {action_type}")
