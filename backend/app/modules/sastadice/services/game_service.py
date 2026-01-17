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
        self, game_id: str, player_name: str, tiles: list[TileCreate]
    ) -> Player:
        """Join a game and submit tiles."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot join game that is not in LOBBY status")

        if len(tiles) != 5:
            raise ValueError("Must submit exactly 5 tiles")

        player_create = PlayerCreate(name=player_name)
        player = self.repository.add_player(game_id, player_create)
        self.repository.submit_tiles(game_id, player.id, tiles)

        # Reload game to include new player
        game = self.get_game(game_id)
        player = next((p for p in game.players if p.id == player.id), player)
        player.submitted_tiles = tiles

        return player

    def start_game(self, game_id: str) -> GameSession:
        """Start a game and generate the board."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game must be in LOBBY status to start")

        if len(game.players) < 2:
            raise ValueError("Need at least 2 players to start game")

        # Collect all player tiles
        all_player_tiles = []
        for player in game.players:
            for tile_create in player.submitted_tiles:
                # Convert TileCreate to Tile
                tile = Tile(
                    type=tile_create.type,
                    name=tile_create.name,
                    effect_config=tile_create.effect_config,
                )
                all_player_tiles.append(tile)

        # Calculate board dimensions
        board_size, _, padding = self.board_service.calculate_dimensions(
            len(game.players)
        )

        # Generate board
        board = self.board_service.generate_board(
            all_player_tiles, board_size, padding
        )

        # Save board to database
        self.repository.save_board(game_id, board)

        # Update game status and set first player's turn
        game.status = GameStatus.ACTIVE
        game.board = board
        game.board_size = board_size
        game.current_turn_player_id = game.players[0].id if game.players else None

        # Update game in database
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

        # Move player
        player = next((p for p in game.players if p.id == player_id), None)
        if player:
            new_position = (player.position + total) % len(game.board)
            self.repository.update_player_position(player_id, new_position)

        # Update game version for polling
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

            # Move to next player
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
            # Placeholder for buy property logic
            return ActionResult(
                success=False, message="Buy property not yet implemented"
            )

        else:
            return ActionResult(success=False, message=f"Unknown action: {action_type}")
