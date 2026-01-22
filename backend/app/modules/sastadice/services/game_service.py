"""Game orchestrator - single entry point coordinating all game managers."""
import random
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.services.board_generation_service import (
    BoardGenerationService,
    GameConfig,
    SASTA_EVENTS,
)
from app.modules.sastadice.services.turn_manager import TurnManager
from app.modules.sastadice.services.auction_manager import AuctionManager
from app.modules.sastadice.services.trade_manager import TradeManager
from app.modules.sastadice.services.economy_manager import EconomyManager
from app.modules.sastadice.services.cpu_manager import CpuManager
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    Player,
    PlayerCreate,
    TileCreate,
    Tile,
    TileType,
    DiceRollResult,
    ActionType,
    ActionResult,
    WinCondition,
    GameSettings,
    TradeOffer,
)


class GameOrchestrator:
    """Single entry point for all game operations. Coordinates managers."""

    def __init__(self, database: "AsyncIOMotorDatabase") -> None:
        """Initialize game service with MongoDB database."""
        self.repository = GameRepository(database)
        self.board_service = BoardGenerationService()
        self.turn_manager = TurnManager()
        self.auction_manager = AuctionManager()
        self.trade_manager = TradeManager()
        self.economy_manager = EconomyManager(self.repository)
        self.cpu_manager = CpuManager(self)

    def _is_cpu_player(self, player: Player) -> bool:
        """Check if a player is a CPU."""
        return self.cpu_manager.is_cpu_player(player)

    def _initialize_event_deck(self, game: GameSession) -> None:
        """Initialize and shuffle the event deck."""
        self.turn_manager.initialize_event_deck(game)

    def _ensure_deck_capacity(self, game: GameSession, count: int = 3) -> None:
        """Ensure deck has enough cards by reshuffling discard if needed."""
        self.turn_manager.ensure_deck_capacity(game, count)

    def _draw_event(self, game: GameSession) -> Optional[dict]:
        """Draw next event from deck."""
        return self.turn_manager.draw_event(game)

    def _calculate_go_bonus(self, game: GameSession) -> int:
        """Calculate GO bonus with inflation using game settings."""
        return self.turn_manager.calculate_go_bonus(game)

    def _owns_full_set(self, player: Player, color: str, board: list[Tile]) -> bool:
        """Check if player owns all properties of a color."""
        return self.turn_manager.owns_full_set(player, color, board)

    def _calculate_rent(self, tile: Tile, owner: Player, game: GameSession) -> int:
        """Calculate rent with set bonus and upgrades."""
        return self.turn_manager.calculate_rent(tile, owner, game)

    async def _send_to_jail(self, game: GameSession, player: Player) -> None:
        """Send player to Server Downtime (jail)."""
        jail_pos = len(game.board) // 2
        player.position = jail_pos
        player.in_jail = True
        player.jail_turns = 0
        await self.repository.update_player_position(player.id, jail_pos)
        game.last_event_message = f"🚨 {player.name} sent to SERVER DOWNTIME!"

    async def _cpu_upgrade_properties(self, game: GameSession, cpu_player: Player) -> bool:
        """CPU attempts to upgrade properties if beneficial. Returns True if upgraded."""
        return await self.cpu_manager.cpu_upgrade_properties(game, cpu_player, self.turn_manager)

    async def _play_cpu_turn(self, game: GameSession, cpu_player: Player) -> list[str]:
        """Play a full CPU turn until turn is complete, return log of actions."""
        return await self.cpu_manager.play_cpu_turn(game, cpu_player)

    async def process_cpu_turns(self, game_id: str) -> dict:
        """Process all consecutive CPU turns until a human player's turn."""
        return await self.cpu_manager.process_cpu_turns(game_id)

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

    async def get_game(self, game_id: str) -> GameSession:
        """Get game session by ID."""
        game = await self.repository.get_by_id(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        return game

    async def update_settings(self, game_id: str, host_id: str, settings_dict: dict) -> dict:
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
        self, game_id: str, player_name: str, tiles: Optional[list[TileCreate]] = None
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

    async def kick_player(self, game_id: str, host_id: str, target_player_id: str) -> dict:
        """Kick a player from the game. Only host can kick."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot kick players after game has started")

        if game.host_id != host_id:
            raise ValueError("Only the host can kick players")

        if target_player_id == host_id:
            raise ValueError("Cannot kick yourself")

        target_player = next((p for p in game.players if p.id == target_player_id), None)
        if not target_player:
            raise ValueError("Player not found in this game")

        await self.repository.remove_player(game_id, target_player_id)

        return {"kicked": True, "player_id": target_player_id, "player_name": target_player.name}

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
            await self.start_game(game_id, force=True)
            game_started = True

        return {
            "player_id": player_id,
            "ready": new_ready,
            "all_ready": all_ready,
            "game_started": game_started,
        }

    async def start_game(self, game_id: str, force: bool = False) -> GameSession:
        """Start a game and generate the board."""
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
        await self.repository.set_players_starting_cash(game_id, game_config.starting_cash)

        game.status = GameStatus.ACTIVE
        game.turn_phase = TurnPhase.PRE_ROLL
        game.board = board
        game.board_size = board_size
        game.current_turn_player_id = game.players[0].id if game.players else None
        game.starting_cash = game_config.starting_cash
        game.go_bonus = game_config.go_bonus
        game.turn_start_time = time.time()

        self.turn_manager.initialize_event_deck(game)

        await self.repository.update(game)
        return await self.get_game(game_id)

    async def roll_dice(self, game_id: str, player_id: str) -> DiceRollResult:
        """Roll dice for a player."""
        game = await self.get_game(game_id)

        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game must be ACTIVE to roll dice")

        if game.current_turn_player_id != player_id:
            raise ValueError("Not your turn")

        if game.turn_phase != TurnPhase.PRE_ROLL:
            raise ValueError("Cannot roll dice in current turn phase")

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            raise ValueError("Player not found")

        if player.in_jail:
            player.jail_turns += 1
            if player.jail_turns >= 1:
                player.in_jail = False
                player.jail_turns = 0
                player.consecutive_doubles = 0
                game.last_event_message = f"✅ {player.name} released from SERVER DOWNTIME!"
            else:
                game.last_event_message = f"⏳ {player.name} stuck in SERVER DOWNTIME. Wait or pay $50 bribe."
                game.turn_phase = TurnPhase.POST_TURN
                await self.repository.update(game)
                return DiceRollResult(dice1=0, dice2=0, total=0, is_doubles=False)

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
                await self._send_to_jail(game, player)
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
                return DiceRollResult(dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles)
        else:
            player.consecutive_doubles = 0

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

        landed_tile = game.board[new_position] if new_position < len(game.board) else None

        if landed_tile:
            await self._handle_tile_landing(game, player, landed_tile)
        
        if game.turn_phase == TurnPhase.DECISION and not game.pending_decision:
            game.turn_phase = TurnPhase.POST_TURN

        await self.repository.update(game)

        return DiceRollResult(
            dice1=dice1, dice2=dice2, total=total, is_doubles=is_doubles
        )

    async def _handle_tile_landing(
        self, game: GameSession, player: Player, tile: Tile
    ) -> None:
        """Handle what happens when a player lands on a tile."""
        if tile.type == TileType.GO:
            self._handle_go_landing(game, tile)
        elif tile.type == TileType.PROPERTY:
            await self._handle_property_landing(game, player, tile)
        elif tile.type == TileType.CHANCE:
            await self._handle_chance_landing(game, player, tile)
        elif tile.type == TileType.TAX:
            await self._handle_tax_landing(game, player, tile)
        elif tile.type == TileType.BUFF:
            await self._handle_buff_landing(game, player, tile)
        elif tile.type == TileType.TRAP:
            await self._handle_trap_landing(game, player, tile)
        elif tile.type == TileType.JAIL:
            self.turn_manager.handle_jail_landing(game)
        elif tile.type == TileType.TELEPORT:
            await self._handle_glitch(game, player)
        elif tile.type == TileType.MARKET:
            self._handle_market_landing(game)
        else:
            game.last_event_message = f"Landed on '{tile.name}'. Nothing happens."
            game.turn_phase = TurnPhase.POST_TURN

    def _handle_go_landing(self, game: GameSession, tile: Tile) -> None:
        self.turn_manager.handle_go_landing(game, tile)

    async def _handle_property_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        result =         result = self.turn_manager.handle_property_landing(game, player, tile)
        if result.get("action") == "pay_rent":
            await self._handle_owned_property_landing(game, player, tile)

    async def _handle_owned_property_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        owner = next((p for p in game.players if p.id == tile.owner_id), None)
        if owner:
            rent = self.turn_manager.calculate_rent(tile, owner, game)
            
            if player.active_buff == "VPN":
                player.active_buff = None
                game.last_event_message = f"🛡️ VPN activated! Blocked ${rent} rent to {owner.name}!"
            else:
                await self._charge_player(game, player, rent, owner)
                if not player.is_bankrupt:
                    bonus_info = ""
                    if tile.color and self.turn_manager.owns_full_set(owner, tile.color, game.board):
                        bonus_info = " (SET BONUS!)"
                    if tile.upgrade_level > 0:
                        level_name = "SCRIPT KIDDIE" if tile.upgrade_level == 1 else "1337 HAXXOR"
                        bonus_info += f" [{level_name}]"
                    
                    game.last_event_message = f"💸 Paid ${rent} rent to {owner.name}{bonus_info}"
        game.turn_phase = TurnPhase.POST_TURN

    async def _handle_chance_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        event = self.turn_manager.handle_chance_landing(game, player, tile)
        actions = self.turn_manager.apply_event_effect(game, player, event)
        
        for pid, amount in actions.get("cash_changes", {}).items():
            p = next((pl for pl in game.players if pl.id == pid), None)
            if p:
                p.cash += amount
                await self.repository.update_player_cash(pid, p.cash)
        
        for pid, new_pos in actions.get("position_changes", {}).items():
            p = next((pl for pl in game.players if pl.id == pid), None)
            if p:
                p.position = new_pos
                await self.repository.update_player_position(pid, new_pos)
        
        if actions.get("skip_buy"):
            game.pending_decision = None
        
        game.last_event_message = f"🎲 {event['name']}: {event['desc']}"
        game.turn_phase = TurnPhase.POST_TURN

    async def _handle_tax_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        tax_amount = self.turn_manager.handle_tax_landing(game, player, tile)
        await self._charge_player(game, player, tax_amount)
        if not player.is_bankrupt:
            game.last_event_message = f"💸 Paid ${tax_amount} in taxes for '{tile.name}'"

    async def _handle_buff_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        buff_amount = self.turn_manager.handle_buff_landing(game, player, tile)
        player.cash += buff_amount
        await self.repository.update_player_cash(player.id, player.cash)
        game.last_event_message = f"🎁 Received ${buff_amount} from '{tile.name}'!"

    async def _handle_trap_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        trap_amount = self.turn_manager.handle_trap_landing(game, player, tile)
        await self._charge_player(game, player, trap_amount)
        if not player.is_bankrupt:
            game.last_event_message = f"⚠️ Lost ${trap_amount} from '{tile.name}'!"

    def _handle_market_landing(self, game: GameSession) -> None:
        self.turn_manager.handle_market_landing(game)

    async def _handle_glitch(self, game: GameSession, player: Player) -> None:
        """Handle The Glitch tile: teleport to random unowned property."""
        target = self.turn_manager.handle_glitch_teleport(game, player)
        if target:
            player.position = target.position
            await self.repository.update_player_position(player.id, target.position)
            game.last_event_message = f"⚡ GLITCH! {player.name} teleported to {target.name}!"
            
            if target.type in [TileType.PROPERTY, TileType.CHANCE, TileType.TAX, TileType.BUFF]:
                await self._handle_tile_landing(game, player, target)
            else:
                game.turn_phase = TurnPhase.POST_TURN

    async def _handle_sasta_event(
        self, game: GameSession, player: Player, tile: Tile
    ) -> dict:
        """Process Sasta Event effects."""
        event = self.turn_manager.draw_event(game)
        if not event:
            event = random.choice(SASTA_EVENTS)

        actions = self.turn_manager.apply_event_effect(game, player, event)
        
        for pid, amount in actions.get("cash_changes", {}).items():
            p = next((pl for pl in game.players if pl.id == pid), None)
            if p:
                if amount < 0:
                    await self._charge_player(game, p, abs(amount), player if pid != player.id else None)
                else:
                    p.cash += amount
                    await self.repository.update_player_cash(pid, p.cash)
        
        for pid, new_pos in actions.get("position_changes", {}).items():
            p = next((pl for pl in game.players if pl.id == pid), None)
            if p:
                p.position = new_pos
                await self.repository.update_player_position(pid, new_pos)
        
        if actions.get("skip_buy"):
            game.pending_decision = None

        return event

    async def perform_action(
        self, game_id: str, player_id: str, action_type: ActionType, payload: dict
    ) -> ActionResult:
        """Dispatch game action to appropriate manager."""
        game = await self.get_game(game_id)

        match action_type:
            case ActionType.ROLL_DICE:
                return await self._handle_roll_dice(game, player_id)
            case ActionType.BUY_PROPERTY:
                return await self._handle_buy_property(game, player_id)
            case ActionType.PASS_PROPERTY:
                return await self._handle_pass_property(game, player_id)
            case ActionType.BID:
                return await self._handle_bid(game, player_id, payload)
            case ActionType.RESOLVE_AUCTION:
                return await self._resolve_auction(game)
            case ActionType.UPGRADE:
                return await self._handle_upgrade(game, player_id, payload)
            case ActionType.DOWNGRADE:
                return await self._handle_downgrade(game, player_id, payload)
            case ActionType.BUY_BUFF:
                return await self._handle_buy_buff(game, player_id, payload)
            case ActionType.BLOCK_TILE:
                return await self._handle_block_tile(game, player_id, payload)
            case ActionType.PROPOSE_TRADE:
                return await self._handle_propose_trade(game, player_id, payload)
            case ActionType.ACCEPT_TRADE:
                return await self._handle_accept_trade(game, player_id, payload)
            case ActionType.DECLINE_TRADE:
                return await self._handle_decline_trade(game, player_id, payload)
            case ActionType.CANCEL_TRADE:
                return await self._handle_cancel_trade(game, player_id, payload)
            case ActionType.END_TURN:
                return await self._handle_end_turn(game, player_id)
            case _:
                return ActionResult(success=False, message=f"Unknown action: {action_type}")

    async def _handle_roll_dice(self, game: GameSession, player_id: str) -> ActionResult:
        try:
            dice_result = await self.roll_dice(game.id, player_id)
            updated_game = await self.get_game(game.id)
            player_idx = next(i for i, p in enumerate(updated_game.players) if p.id == player_id)
            return ActionResult(
                success=True,
                message=updated_game.last_event_message or "Dice rolled",
                data={
                    **dice_result.model_dump(),
                    "new_position": updated_game.players[player_idx].position,
                    "turn_phase": updated_game.turn_phase.value,
                    "pending_decision": updated_game.pending_decision.model_dump() if updated_game.pending_decision else None,
                },
            )
        except ValueError as e:
            return ActionResult(success=False, message=str(e))

    async def _handle_buy_property(self, game: GameSession, player_id: str) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        success, message, tile_name, price = await self.economy_manager.handle_buy_property(game, player_id)
        
        if success and tile_name and price:
            game.last_event_message = f"🏠 Bought '{tile_name}' for ${price}!"
            await self.repository.update(game)
        
        return ActionResult(success=success, message=message)

    async def _handle_pass_property(self, game: GameSession, player_id: str) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        if game.turn_phase != TurnPhase.DECISION:
            return ActionResult(success=False, message="Cannot pass now")
        
        if game.settings.enable_auctions and game.pending_decision and game.pending_decision.type == "BUY":
            tile_id = game.pending_decision.tile_id
            if not tile_id:
                game.pending_decision = None
                game.turn_phase = TurnPhase.POST_TURN
                game.last_event_message = "Passed on decision."
                await self.repository.update(game)
                return ActionResult(success=True, message="Passed on decision")
            
            tile = next((t for t in game.board if t.id == tile_id), None)
            
            if tile and tile.type == TileType.PROPERTY and not tile.owner_id:
                self.auction_manager.start_auction(game, tile, auction_duration=30)
                await self.repository.update(game)
                return ActionResult(success=True, message=f"Auction started for {tile.name}")

        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        game.last_event_message = "Passed on decision."
        await self.repository.update(game)

        return ActionResult(success=True, message="Passed on decision")

    async def _handle_bid(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        if game.turn_phase != TurnPhase.AUCTION or not game.auction_state:
            return ActionResult(success=False, message="No active auction")
        
        amount = payload.get("amount")
        if not amount:
            return ActionResult(success=False, message="Bid amount required")
        
        if self.auction_manager.check_auction_timeout(game.auction_state):
            return await self._resolve_auction(game)

        success, message = self.auction_manager.place_bid(game, player_id, amount)
        if success:
            await self.repository.update(game)
        return ActionResult(success=success, message=message)

    async def _handle_upgrade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        success, message, level_name = await self.economy_manager.handle_upgrade(
            game, player_id, payload, self.turn_manager
        )
        
        if success and level_name:
            tile_id = payload.get("tile_id")
            tile = next((t for t in game.board if t.id == tile_id), None)
            player = next((p for p in game.players if p.id == player_id), None)
            if tile and player:
                game.last_event_message = f"💻 {player.name} upgraded {tile.name} to {level_name}!"
            await self.repository.update(game)
        
        return ActionResult(success=success, message=message)

    async def _handle_downgrade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        """Sell upgrade for 50% refund."""
        success, message, refund = await self.economy_manager.handle_downgrade(
            game, player_id, payload
        )
        
        if success and refund:
            tile_id = payload.get("tile_id")
            tile = next((t for t in game.board if t.id == tile_id), None)
            player = next((p for p in game.players if p.id == player_id), None)
            if tile and player:
                prev_level_name = "1337 HAXXOR" if tile.upgrade_level == 0 else "SCRIPT KIDDIE"
                game.last_event_message = f"💸 {player.name} sold {prev_level_name} upgrade on {tile.name} for ${refund}"
            await self.repository.update(game)
        
        return ActionResult(success=success, message=message)

    async def _handle_buy_buff(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        if game.turn_phase != TurnPhase.DECISION or not game.pending_decision or game.pending_decision.type != "MARKET":
                return ActionResult(success=False, message="Not in Market")

        buff_id = payload.get("buff_id")
        event_data = game.pending_decision.event_data or {}
        buffs = event_data.get("buffs", [])
        selected_buff = next((b for b in buffs if b["id"] == buff_id), None)
        
        if not selected_buff:
                return ActionResult(success=False, message="Invalid buff")
                
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")

        if player.cash < selected_buff["cost"]:
                return ActionResult(success=False, message="Insufficient funds")

        if buff_id == "PEEK":
            needed = 3
            self._ensure_deck_capacity(game, needed)
            preview_indices = game.event_deck[:needed]
            preview_names = [str(SASTA_EVENTS[idx]["name"]) for idx in preview_indices]
            
            player.cash -= selected_buff["cost"]
            await self.repository.update_player_cash(player.id, player.cash)
            
            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            
            msg = f"🔎 Insider Info! Next Events: {', '.join(preview_names)}"
            game.last_event_message = msg
            await self.repository.update(game)
            return ActionResult(success=True, message=msg)

        player.cash -= selected_buff["cost"]
        player.active_buff = buff_id
        await self.repository.update_player_cash(player.id, player.cash)
        await self.repository.update_player_buff(player.id, buff_id)
        
        game.pending_decision = None
        game.turn_phase = TurnPhase.POST_TURN
        game.last_event_message = f"🛒 {player.name} bought {selected_buff['name']}!"
        await self.repository.update(game)
        return ActionResult(success=True, message=f"Bought {selected_buff['name']}")

    async def _handle_block_tile(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")
        
        if game.turn_phase not in (TurnPhase.POST_TURN, TurnPhase.PRE_ROLL):
            return ActionResult(success=False, message="Cannot use DDoS in current phase")
        
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")
        
        if player.active_buff != "DDOS":
            return ActionResult(success=False, message="You don't have the DDoS buff")

        target_tile_id = payload.get("tile_id")
        if not target_tile_id:
            return ActionResult(success=False, message="Target tile required")
        
        tile = next((t for t in game.board if t.id == target_tile_id), None)
        if not tile:
            return ActionResult(success=False, message="Invalid tile")
        
        tile.blocked_until_round = game.current_round + 1
        player.active_buff = None
        
        await self.repository.update_player_buff(player.id, None)
        await self.repository.save_board(game.id, game.board)
        
        game.last_event_message = f"💀 DDoS ATTACK! {tile.name} disabled for 1 round by {player.name}!"
        await self.repository.update(game)
        return ActionResult(success=True, message=f"Disabled {tile.name}")

    async def _handle_propose_trade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Can only propose trades on your turn")
        
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return ActionResult(success=False, message="Player not found")
        
        offer, error = self.trade_manager.create_trade_offer(game, player, payload)
        if error:
            return ActionResult(success=False, message=error)
        
        if offer:
            target_player = next((p for p in game.players if p.id == offer.target_id), None)
            game.active_trade_offers.append(offer)
            game.last_event_message = f"🤝 {player.name} proposed a trade to {target_player.name if target_player else 'Unknown'}!"
            await self.repository.update(game)
            return ActionResult(success=True, message="Trade offered")
        
        return ActionResult(success=False, message="Failed to create trade offer")

    async def _handle_accept_trade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade offer not found")
        
        if offer.target_id != player_id:
            return ActionResult(success=False, message="Not authorized to accept this trade")

        initiator = next((p for p in game.players if p.id == offer.initiator_id), None)
        player = next((p for p in game.players if p.id == player_id), None)
        
        if not initiator:
            game.active_trade_offers.remove(offer)
            await self.repository.update(game)
            return ActionResult(success=False, message="Initiator gone")

        if not player:
            game.active_trade_offers.remove(offer)
            await self.repository.update(game)
            return ActionResult(success=False, message="Player not found")

        validation_error = self._validate_trade_assets(game, offer, initiator, player)
        if validation_error:
             return ActionResult(success=False, message=validation_error)

        await self._execute_trade_transfer(game, offer, initiator, player)
        
        game.active_trade_offers.remove(offer)
        game.last_event_message = f"🤝 Trade accepted between {initiator.name} and {player.name}!"
        await self.repository.update(game)
        return ActionResult(success=True, message="Trade completed")

    def _validate_trade_assets(self, game: GameSession, offer: TradeOffer, initiator: Player, target: Player) -> str | None:
        return self.trade_manager.validate_trade_assets(game, offer, initiator, target)

    async def _execute_trade_transfer(self, game: GameSession, offer: TradeOffer, initiator: Player, target: Player) -> None:
        transfer_data = self.trade_manager.execute_trade_transfer(game, offer, initiator, target)
        
        initiator.cash = transfer_data["initiator_cash"]
        target.cash = transfer_data["target_cash"]
        
        await self.repository.update_player_cash(initiator.id, initiator.cash)
        await self.repository.update_player_cash(target.id, target.cash)

        for pid in transfer_data["property_transfers"]["initiator_to_target"]:
            tile = next((t for t in game.board if t.id == pid), None)
            if tile:
                tile.owner_id = target.id
        
        for pid in transfer_data["property_transfers"]["target_to_initiator"]:
            tile = next((t for t in game.board if t.id == pid), None)
            if tile:
                tile.owner_id = initiator.id
        
        await self.repository.save_board(game.id, game.board)

    async def _handle_decline_trade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade not found")
        
        if offer.target_id != player_id:
            return ActionResult(success=False, message="Not authorized")
        
        player = next((p for p in game.players if p.id == player_id), None)
        game.active_trade_offers.remove(offer)
        player_name = player.name if player else "Unknown"
        game.last_event_message = f"🚫 {player_name} declined trade."
        await self.repository.update(game)
        return ActionResult(success=True, message="Declined")

    async def _handle_cancel_trade(self, game: GameSession, player_id: str, payload: dict) -> ActionResult:
        trade_id = payload.get("trade_id")
        offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
        if not offer:
            return ActionResult(success=False, message="Trade not found")
        
        if offer.initiator_id != player_id:
                return ActionResult(success=False, message="Not authorized")

        game.active_trade_offers.remove(offer)
        await self.repository.update(game)
        return ActionResult(success=True, message="Cancelled")

    async def _handle_end_turn(self, game: GameSession, player_id: str) -> ActionResult:
        if game.current_turn_player_id != player_id:
            return ActionResult(success=False, message="Not your turn")

        if game.turn_phase != TurnPhase.POST_TURN:
            return ActionResult(
                success=False,
                message=f"Cannot end turn in {game.turn_phase.value} phase"
            )

        player = next((p for p in game.players if p.id == player_id), None)
        if player and game.last_dice_roll and game.last_dice_roll.get("is_doubles"):
            game.turn_phase = TurnPhase.PRE_ROLL
            game.pending_decision = None
            game.last_dice_roll = None
            game.last_event_message = f"🎲 DOUBLES! {player.name} rolls again!"
            await self.repository.update(game)
            return ActionResult(success=True, message=f"Doubles! Roll again!")

        if await self._check_and_handle_end_conditions(game.id):
            updated_game = await self.get_game(game.id)
            winner = self._determine_winner(updated_game)
            if not winner:
                return ActionResult(success=False, message="Could not determine winner")
            return ActionResult(
                success=True,
                message=f"🏆 Game Over! {winner['name']} wins!",
                data={"game_over": True, "winner": winner}
            )

        game = await self.get_game(game.id)
        
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
        if next_player.id == game.first_player_id:
            game.current_round += 1
            
            for tile in game.board:
                if tile.blocked_until_round and tile.blocked_until_round <= game.current_round:
                    tile.blocked_until_round = None
            
            if (game.settings.win_condition == WinCondition.SUDDEN_DEATH and 
                game.settings.round_limit > 0 and
                game.current_round >= game.settings.round_limit):
                winner = self._determine_winner(game)
                if not winner:
                    return ActionResult(success=False, message="Could not determine winner")
                game.status = GameStatus.FINISHED
                await self.repository.save_board(game.id, game.board)
                await self.repository.update(game)
                return ActionResult(
                    success=True,
                    message=f"⏰ ROUND {game.settings.round_limit}! SUDDEN DEATH! {winner['name']} wins with ${winner['cash']}!",
                    data={"game_over": True, "winner": winner, "sudden_death": True}
                )

        game.current_turn_player_id = next_player.id
        game.turn_phase = TurnPhase.PRE_ROLL
        game.pending_decision = None
        game.last_dice_roll = None
        game.last_event_message = None
        game.turn_start_time = time.time()

        if game.current_round > old_round:
            await self.repository.save_board(game.id, game.board)

        await self.repository.update(game)

        round_limit_display = game.settings.round_limit if game.settings.round_limit > 0 else "∞"
        round_info = f" [Round {game.current_round}/{round_limit_display}]"
        return ActionResult(success=True, message=f"Turn ended. {next_player.name}'s turn!{round_info}")

    async def simulate_cpu_game(self, game_id: str, max_turns: int = 100) -> dict:
        """Simulate a CPU-only game until completion or max turns."""
        game = await self.get_game(game_id)
        
        if game.status == GameStatus.LOBBY:
            if len(game.players) < 2:
                raise ValueError("Need at least 2 CPU players to simulate")
            game = await self.start_game(game_id, force=True)
        
        if game.status != GameStatus.ACTIVE:
            raise ValueError(f"Game is not active: {game.status}")
        
        turns_played = 0
        turn_log = []
        stuck_state = {"counter": 0, "last_state": None}
        
        while turns_played < max_turns and game.status == GameStatus.ACTIVE:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player:
                break
            
            await self._handle_stuck_state(game, current_player, stuck_state)
            
            turn_info = self._init_turn_info(game, current_player, turns_played)
            
            game_over = await self._execute_simulated_turn(game_id, current_player, turn_info)
            if game_over:
                turn_log.append(turn_info)
                break
            
            self._update_turn_info_post_turn(game, turn_info)
            turn_log.append(turn_info)
            turns_played += 1
            
            game = await self._check_bankruptcy(game_id)
            if self._check_simulation_end(game):
                break
        
        game = await self.get_game(game_id)
        return self._build_simulation_result(game, turns_played, turn_log)

    async def _handle_stuck_state(self, game: GameSession, current_player: Player, stuck_state: dict) -> None:
        current_state = f"{game.turn_phase.value}:{current_player.id}:{game.pending_decision}"
        if current_state == stuck_state["last_state"]:
            stuck_state["counter"] += 1
            if stuck_state["counter"] > 5:
                game.turn_phase = TurnPhase.POST_TURN
                game.pending_decision = None
                await self.repository.update(game)
                stuck_state["counter"] = 0
        else:
            stuck_state["counter"] = 0
            stuck_state["last_state"] = current_state

    def _init_turn_info(self, game: GameSession, current_player: Player, turns_played: int) -> dict:
        return {
            "turn": turns_played + 1,
            "round": game.current_round,
            "player": current_player.name,
            "player_id": current_player.id,
            "cash_before": current_player.cash,
            "position_before": current_player.position,
            "in_jail": current_player.in_jail,
            "actions": [],
        }

    def _update_turn_info_post_turn(self, game: GameSession, turn_info: dict) -> None:
        current_player = next(
            (p for p in game.players if p.id == turn_info["player_id"]), None
        )
        if current_player:
            turn_info["cash_after"] = current_player.cash
            turn_info["position_after"] = current_player.position

    def _check_simulation_end(self, game: GameSession) -> bool:
        active_players = [p for p in game.players if not p.is_bankrupt and p.cash >= 0]
        if len(active_players) <= 1:
            game.status = GameStatus.FINISHED
            return True
        return False
        
    def _build_simulation_result(self, game: GameSession, turns_played: int, turn_log: list) -> dict:
        return {
            "game_id": game.id,
            "status": game.status.value,
            "turns_played": turns_played,
            "rounds_played": game.current_round,
            "max_rounds": game.max_rounds,
            "winner": self._determine_winner(game),
            "final_standings": [
                {"name": p.name, "cash": p.cash, "properties": len(p.properties), "bankrupt": p.is_bankrupt}
                for p in sorted(game.players, key=lambda x: x.cash, reverse=True)
            ],
            "turn_log": turn_log[-10:],
        }

    async def _execute_simulated_turn(self, game_id: str, current_player: Player, turn_info: dict) -> bool:
        """Execute a single turn in the simulation. Returns True if game over."""
        game = await self.get_game(game_id)
        
        if game.turn_phase == TurnPhase.PRE_ROLL:
            result = await self.perform_action(game_id, current_player.id, ActionType.ROLL_DICE, {})
            turn_info["actions"].append({"action": "ROLL_DICE", "result": result.message})
            game = await self.get_game(game_id)
        
        if game.turn_phase == TurnPhase.DECISION and game.pending_decision:
            await self._handle_simulated_decision(game_id, current_player, turn_info)
            game = await self.get_game(game_id)
        
        await self._simulate_cpu_trades(game, turn_info)
        game = await self.get_game(game_id)

        if game.turn_phase == TurnPhase.POST_TURN:
            result = await self.perform_action(game_id, current_player.id, ActionType.END_TURN, {})
            turn_info["actions"].append({"action": "END_TURN", "result": result.message})
            game = await self.get_game(game_id)
            
            if result.data and result.data.get("game_over"):
                turn_info["actions"].append({"action": "GAME_OVER", "result": result.message})
                return True
        
        return False

    async def _handle_simulated_decision(self, game_id: str, current_player: Player, turn_info: dict) -> None:
        """Handle decision phase in simulation."""
        game = await self.get_game(game_id)
        if not game.pending_decision:
            return

        game_current_player = next(
            (p for p in game.players if p.id == game.current_turn_player_id), None
        )
        if not game_current_player:
            return
        
        decision_type = game.pending_decision.type
        
        if decision_type == "BUY":
            price = game.pending_decision.price
            if game_current_player and game_current_player.cash >= price * 1.5:
                result = await self.perform_action(game_id, game_current_player.id, ActionType.BUY_PROPERTY, {})
                turn_info["actions"].append({"action": "BUY_PROPERTY", "result": result.message})
            else:
                result = await self.perform_action(game_id, game_current_player.id, ActionType.PASS_PROPERTY, {})
                turn_info["actions"].append({"action": "PASS_PROPERTY", "result": result.message})
        
        elif decision_type == "MARKET":
            buffs = game.pending_decision.event_data.get("buffs", []) if game.pending_decision.event_data else []
            bought = False
            
            if game_current_player and not game_current_player.active_buff:
                for buff in buffs:
                    if game_current_player and game_current_player.cash >= buff["cost"] + 300:
                        result = await self.perform_action(game_id, game_current_player.id, ActionType.BUY_BUFF, {"buff_id": buff["id"]})
                        turn_info["actions"].append({"action": "BUY_BUFF", "result": result.message})
                        bought = True
                        break
            
            if not bought:
                result = await self.perform_action(game_id, current_player.id, ActionType.PASS_PROPERTY, {})
                turn_info["actions"].append({"action": "PASS_MARKET", "result": result.message})
        
        else:
            turn_info["actions"].append({"action": f"SKIP_{decision_type}", "result": f"Skipped unknown decision: {decision_type}"})
            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            await self.repository.update(game)
    
    async def _resolve_auction(self, game: GameSession) -> ActionResult:
        """Resolve a finished auction."""
        success, message, winner_id, amount, prop_id = self.auction_manager.resolve_auction(game)
        
        if not success:
            return ActionResult(success=False, message=message)
        
        if winner_id and prop_id:
            winner = next((p for p in game.players if p.id == winner_id), None)
            if winner:
                winner.cash -= amount
                winner.properties.append(prop_id)
                await self.repository.update_player_cash(winner.id, winner.cash)
                await self.repository.update_player_properties(winner.id, winner.properties)
                await self.repository.update_tile_owner(prop_id, winner.id)
        
        await self.repository.update(game)
        
        final_message = game.last_event_message or message
        return ActionResult(success=True, message=final_message)

    async def _auto_liquidate(self, game: GameSession, player: Player, needed: int) -> int:
        """Attempt to raise cash by downgrading/selling assets (Fire Sale)."""
        return await self.economy_manager.auto_liquidate(game, player, needed)

    async def _process_bankruptcy(self, game: GameSession, debtor: Player, creditor: Player | None = None):
        """Handle bankruptcy: asset transfer or seizure."""
        await self.economy_manager.process_bankruptcy(game, debtor, creditor)

    async def _charge_player(self, game: GameSession, player: Player, amount: int, creditor: Player | None = None):
        """Charge a player amount. Trigger Fire Sale or Bankruptcy if needed."""
        result = await self.economy_manager.charge_player(game, player, amount, creditor)
        
        if result["action"] == "charged":
            return
        elif result["action"] == "charged_after_liquidation":
            game.last_event_message = (game.last_event_message or "") + " | 📉 FIRE SALE triggered! | Survived by selling assets."
        elif result["action"] == "bankrupt":
            game.last_event_message = (game.last_event_message or "") + " | 📉 FIRE SALE triggered!"

    async def _simulate_cpu_trades(self, game: GameSession, turn_info: dict) -> None:
        """Handle CPU trading logic (Propose/Accept/Decline)."""
        await self._process_incoming_trade_offers(game, turn_info)

        current_player = next((p for p in game.players if p.id == game.current_turn_player_id), None)
        if game.turn_phase == TurnPhase.POST_TURN and current_player:
             await self._attempt_cpu_trade_proposal(game, current_player, turn_info)

    async def _process_incoming_trade_offers(self, game: GameSession, turn_info: dict) -> None:
        """Process trade offers sent to CPU players."""
        for offer in list(game.active_trade_offers):
            target = next((p for p in game.players if p.id == offer.target_id), None)
            if target: 
                if random.random() < 0.3:
                    res = await self.perform_action(game.id, target.id, ActionType.ACCEPT_TRADE, {"trade_id": offer.id})
                    turn_info["actions"].append({"action": f"ACCEPT_TRADE ({target.name})", "result": res.message})
                else:
                    res = await self.perform_action(game.id, target.id, ActionType.DECLINE_TRADE, {"trade_id": offer.id})
                    turn_info["actions"].append({"action": f"DECLINE_TRADE ({target.name})", "result": res.message})

    async def _attempt_cpu_trade_proposal(self, game: GameSession, current_player: Player, turn_info: dict) -> None:
        """Attempt to propose a trade from the current CPU player."""
        if random.random() >= 0.1:
            return

        potential_targets = [p for p in game.players if p.id != current_player.id]
        if not potential_targets:
            return
        
        target = random.choice(potential_targets)
        
        my_props = [t.id for t in game.board if t.owner_id == current_player.id]
        their_props = [t.id for t in game.board if t.owner_id == target.id]
        
        offer_props = [random.choice(my_props)] if my_props and random.random() < 0.5 else []
        req_props = [random.choice(their_props)] if their_props and random.random() < 0.5 else []
        
        offer_cash = min(current_player.cash, 100) if random.random() < 0.5 else 0
        
        if not offer_props and not req_props and offer_cash == 0:
            return
        
        payload = {
            "target_id": target.id,
            "offer_cash": offer_cash,
            "req_cash": 0,
            "offer_props": offer_props,
            "req_props": req_props
        }
        
        res = await self.perform_action(game.id, current_player.id, ActionType.PROPOSE_TRADE, payload)
        turn_info["actions"].append({"action": "PROPOSE_TRADE", "result": res.message})


    async def _check_bankruptcy(self, game_id: str) -> GameSession:
        """Check for bankrupt players and mark them."""
        game = await self.get_game(game_id)
        
        for player in game.players:
            if player.cash < 0:
                player.cash = -9999
                await self.repository.update_player_cash(player.id, player.cash)
        
        return await self.get_game(game_id)

    async def check_timeout(self, game_id: str) -> bool:
        """Check if current turn has timed out and force end if needed."""
        game = await self.get_game(game_id)
        
        if game.status != GameStatus.ACTIVE:
            return False
        
        if not game.turn_start_time or game.turn_start_time == 0:
            return False
        
        timeout_seconds = game.settings.turn_timer_seconds
        elapsed = time.time() - game.turn_start_time
        
        if elapsed > timeout_seconds:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player:
                return False
            
            if game.turn_phase == TurnPhase.PRE_ROLL:
                await self.perform_action(game_id, current_player.id, ActionType.ROLL_DICE, {})
            elif game.turn_phase == TurnPhase.DECISION:
                await self.perform_action(game_id, current_player.id, ActionType.PASS_PROPERTY, {})
            elif game.turn_phase == TurnPhase.POST_TURN:
                await self.perform_action(game_id, current_player.id, ActionType.END_TURN, {})
            
            return True
        
        return False

    async def _force_end_turn(self, game: GameSession) -> None:
        """Force end turn by auto-rolling or auto-passing based on phase."""
        current_player = next(
            (p for p in game.players if p.id == game.current_turn_player_id), None
        )
        if not current_player:
            return
        
        if game.turn_phase == TurnPhase.PRE_ROLL:
            await self.perform_action(game.id, current_player.id, ActionType.ROLL_DICE, {})
        elif game.turn_phase == TurnPhase.DECISION:
            await self.perform_action(game.id, current_player.id, ActionType.PASS_PROPERTY, {})
        elif game.turn_phase == TurnPhase.POST_TURN:
            await self.perform_action(game.id, current_player.id, ActionType.END_TURN, {})

    async def _check_and_handle_end_conditions(self, game_id: str) -> bool:
        """Check for bankruptcy and game end. Returns True if game ended."""
        game = await self.get_game(game_id)
        
        for player in game.players:
            if player.cash < 0 and not player.is_bankrupt:
                player.is_bankrupt = True
                await self.repository.update_player_bankrupt(player.id, True)
        
        active_players = [p for p in game.players if not p.is_bankrupt]
        
        if len(active_players) <= 1:
            game = await self.get_game(game_id)
            game.status = GameStatus.FINISHED
            winner = active_players[0] if active_players else max(game.players, key=lambda x: x.cash)
            game.last_event_message = f"🏆 GAME OVER! {winner.name} wins with ${winner.cash}!"
            await self.repository.update(game)
            return True
        
        return False
    
    def _determine_winner(self, game: GameSession) -> Optional[dict]:
        """Determine the winner of the game."""
        return self.economy_manager.determine_winner(game)


# Backward compatibility alias
GameService = GameOrchestrator
