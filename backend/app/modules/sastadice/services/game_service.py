"""Game service for managing game sessions and actions."""
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.services.board_generation_service import (
    BoardGenerationService,
    GameConfig,
    SASTA_EVENTS,
)
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    PendingDecision,
    Player,
    PlayerCreate,
    TileCreate,
    Tile,
    TileType,
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

    def toggle_ready(self, game_id: str, player_id: str) -> dict:
        """Toggle player's launch key. Auto-starts if all players ready."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game already started")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise ValueError("Player not in this game")

        new_ready = self.repository.toggle_player_ready(player_id)
        self.repository.update(game)  # Bump version for polling

        all_ready = self.repository.are_all_players_ready(game_id)
        game_started = False

        # Auto-start when all human players ready (need at least 1)
        if all_ready and len(game.players) >= 1:
            self.start_game(game_id, force=True)
            game_started = True

        return {
            "player_id": player_id,
            "ready": new_ready,
            "all_ready": all_ready,
            "game_started": game_started,
        }

    def start_game(self, game_id: str, force: bool = False) -> GameSession:
        """Start a game and generate the board."""
        game = self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Game must be in LOBBY status to start")

        # Check all players ready unless forced
        if not force and not self.repository.are_all_players_ready(game_id):
            raise ValueError("All players must turn their launch keys")

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

        total_tiles = len(all_player_tiles) + padding + 1
        game_config = GameConfig(total_tiles, len(game.players))

        board = self.board_service.generate_board(
            all_player_tiles, board_size, padding, game_config
        )

        self.repository.save_board(game_id, board)
        self.repository.set_players_starting_cash(game_id, game_config.starting_cash)

        game.status = GameStatus.ACTIVE
        game.turn_phase = TurnPhase.PRE_ROLL
        game.board = board
        game.board_size = board_size
        game.current_turn_player_id = game.players[0].id if game.players else None
        game.starting_cash = game_config.starting_cash
        game.go_bonus = game_config.go_bonus

        self.repository.update(game)
        return self.get_game(game_id)

    def roll_dice(self, game_id: str, player_id: str) -> DiceRollResult:
        """Roll dice for a player."""
        game = self.get_game(game_id)

        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game must be ACTIVE to roll dice")

        if game.current_turn_player_id != player_id:
            raise ValueError("Not your turn")

        if game.turn_phase != TurnPhase.PRE_ROLL:
            raise ValueError("Cannot roll dice in current turn phase")

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        is_doubles = dice1 == dice2

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise ValueError("Player not found")

        old_position = player.position
        new_position = (player.position + total) % len(game.board)

        passed_go = new_position < old_position and old_position != 0
        if passed_go:
            new_cash = player.cash + game.go_bonus
            self.repository.update_player_cash(player_id, new_cash)
            player.cash = new_cash

        self.repository.update_player_position(player_id, new_position)
        player.position = new_position

        game.last_dice_roll = {
            "dice1": dice1,
            "dice2": dice2,
            "total": total,
            "is_doubles": is_doubles,
            "passed_go": passed_go,
        }

        # Transition to DECISION phase and determine what happens on landed tile
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = None
        game.last_event_message = None

        landed_tile = game.board[new_position] if new_position < len(game.board) else None

        if landed_tile:
            self._handle_tile_landing(game, player, landed_tile)

        self.repository.update(game)

        return DiceRollResult(
            dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles
        )

    def _handle_tile_landing(
        self, game: GameSession, player: Player, tile: Tile
    ) -> None:
        """Handle what happens when a player lands on a tile."""
        if tile.type == TileType.GO:
            # Landing on GO gives bonus (already handled if passed)
            game.last_event_message = f"Welcome to GO! Collect ${game.go_bonus} when you pass."
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.PROPERTY:
            if tile.owner_id is None:
                # Unowned property - offer to buy
                game.pending_decision = PendingDecision(
                    type="BUY",
                    tile_id=tile.id,
                    price=tile.price,
                )
                game.last_event_message = f"'{tile.name}' is for sale! Price: ${tile.price}"
                # Stay in DECISION phase

            elif tile.owner_id == player.id:
                # Own property - nothing happens
                game.last_event_message = f"You own '{tile.name}'. Safe!"
                game.turn_phase = TurnPhase.POST_TURN

            else:
                # Someone else's property - pay rent
                owner = next((p for p in game.players if p.id == tile.owner_id), None)
                if owner:
                    rent = tile.rent
                    player.cash -= rent
                    owner.cash += rent
                    self.repository.update_player_cash(player.id, player.cash)
                    self.repository.update_player_cash(owner.id, owner.cash)
                    game.last_event_message = f"Paid ${rent} rent to {owner.name} for '{tile.name}'"
                game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.CHANCE:
            # Sasta Event!
            event = self._handle_sasta_event(game, player, tile)
            game.last_event_message = f"🎲 {event['name']}: {event['desc']}"
            if event.get("type") != "SKIP_BUY":
                game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.TAX:
            # Pay tax
            tax_amount = tile.price if tile.price > 0 else game.go_bonus // 2
            player.cash -= tax_amount
            self.repository.update_player_cash(player.id, player.cash)
            game.last_event_message = f"💸 Paid ${tax_amount} in taxes for '{tile.name}'"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.BUFF:
            # Receive bonus
            buff_amount = game.go_bonus // 2
            player.cash += buff_amount
            self.repository.update_player_cash(player.id, player.cash)
            game.last_event_message = f"🎁 Received ${buff_amount} from '{tile.name}'!"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.TRAP:
            # Pay penalty
            trap_amount = game.go_bonus // 3
            player.cash -= trap_amount
            self.repository.update_player_cash(player.id, player.cash)
            game.last_event_message = f"⚠️ Lost ${trap_amount} from '{tile.name}'!"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.NEUTRAL:
            # Nothing happens
            game.last_event_message = f"Landed on '{tile.name}'. Nothing happens."
            game.turn_phase = TurnPhase.POST_TURN

        else:
            game.turn_phase = TurnPhase.POST_TURN

    def _handle_sasta_event(
        self, game: GameSession, player: Player, tile: Tile
    ) -> dict:
        """Process Sasta Event effects."""
        event = random.choice(SASTA_EVENTS)

        if event["type"] == "CASH_GAIN":
            player.cash += event["value"]
            self.repository.update_player_cash(player.id, player.cash)

        elif event["type"] == "CASH_LOSS":
            player.cash -= event["value"]
            self.repository.update_player_cash(player.id, player.cash)

        elif event["type"] == "COLLECT_FROM_ALL":
            for p in game.players:
                if p.id != player.id:
                    p.cash -= event["value"]
                    player.cash += event["value"]
                    self.repository.update_player_cash(p.id, p.cash)
            self.repository.update_player_cash(player.id, player.cash)

        elif event["type"] == "SKIP_BUY":
            # Cannot buy property this turn - clear any pending decision
            game.pending_decision = None

        elif event["type"] == "MOVE_BACK":
            new_pos = max(0, player.position - event["value"])
            self.repository.update_player_position(player.id, new_pos)
            player.position = new_pos

        return event

    def perform_action(
        self, game_id: str, player_id: str, action_type: ActionType, payload: dict
    ) -> ActionResult:
        """Perform a game action."""
        game = self.get_game(game_id)

        if action_type == ActionType.ROLL_DICE:
            try:
                dice_result = self.roll_dice(game_id, player_id)
                # Reload game to get updated state
                updated_game = self.get_game(game_id)
                return ActionResult(
                    success=True,
                    message=updated_game.last_event_message or "Dice rolled",
                    data={
                        **dice_result.model_dump(),
                        "new_position": updated_game.players[
                            next(i for i, p in enumerate(updated_game.players) if p.id == player_id)
                        ].position,
                        "turn_phase": updated_game.turn_phase.value,
                        "pending_decision": updated_game.pending_decision.model_dump() if updated_game.pending_decision else None,
                    },
                )
            except ValueError as e:
                return ActionResult(success=False, message=str(e))

        elif action_type == ActionType.BUY_PROPERTY:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Not your turn")

            if game.turn_phase != TurnPhase.DECISION:
                return ActionResult(success=False, message="Cannot buy property now")

            if not game.pending_decision or game.pending_decision.type != "BUY":
                return ActionResult(success=False, message="No property to buy")

            player = next((p for p in game.players if p.id == player_id), None)
            if not player:
                return ActionResult(success=False, message="Player not found")

            tile_id = game.pending_decision.tile_id
            price = game.pending_decision.price

            if player.cash < price:
                return ActionResult(success=False, message=f"Not enough cash. Need ${price}, have ${player.cash}")

            # Buy the property
            player.cash -= price
            player.properties.append(tile_id)
            self.repository.update_player_cash(player_id, player.cash)
            self.repository.update_player_properties(player_id, player.properties)
            self.repository.update_tile_owner(tile_id, player_id)

            # Find tile name for message
            tile = next((t for t in game.board if t.id == tile_id), None)
            tile_name = tile.name if tile else "property"

            # Clear decision and move to POST_TURN
            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            game.last_event_message = f"🏠 Bought '{tile_name}' for ${price}!"
            self.repository.update(game)

            return ActionResult(success=True, message=f"Bought '{tile_name}' for ${price}")

        elif action_type == ActionType.PASS_PROPERTY:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Not your turn")

            if game.turn_phase != TurnPhase.DECISION:
                return ActionResult(success=False, message="Cannot pass now")

            # Clear decision and move to POST_TURN
            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            game.last_event_message = "Passed on buying property."
            self.repository.update(game)

            return ActionResult(success=True, message="Passed on property")

        elif action_type == ActionType.END_TURN:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Not your turn")

            if game.turn_phase != TurnPhase.POST_TURN:
                return ActionResult(
                    success=False,
                    message=f"Cannot end turn in {game.turn_phase.value} phase"
                )

            # Advance to next player
            current_index = next(
                (i for i, p in enumerate(game.players) if p.id == game.current_turn_player_id),
                0,
            )
            next_index = (current_index + 1) % len(game.players)
            next_player = game.players[next_index]

            game.current_turn_player_id = next_player.id
            game.turn_phase = TurnPhase.PRE_ROLL
            game.pending_decision = None
            game.last_dice_roll = None
            game.last_event_message = None

            self.repository.update(game)

            return ActionResult(success=True, message=f"Turn ended. {next_player.name}'s turn!")

        else:
            return ActionResult(success=False, message=f"Unknown action: {action_type}")
