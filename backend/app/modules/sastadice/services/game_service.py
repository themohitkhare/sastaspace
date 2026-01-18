"""Game service for managing game sessions and actions."""
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
    WinCondition,
    GameSettings,
    GameSettings,
    AuctionState,
    TradeOffer,
)

CPU_NAMES = {"ROBOCOP", "CHAD BOT", "KAREN.EXE", "STONKS", "CPU-1", "CPU-2", "CPU-3", "CPU-4", "CPU-5"}


class GameService:
    """Service for game session management and actions."""

    def __init__(self, database) -> None:  # type: ignore
        """Initialize game service with MongoDB database."""
        self.repository = GameRepository(database)
        self.board_service = BoardGenerationService()

    def _is_cpu_player(self, player: Player) -> bool:
        """Check if a player is a CPU."""
        return player.name in CPU_NAMES

    def _initialize_event_deck(self, game: GameSession) -> None:
        """Initialize and shuffle the event deck."""
        game.event_deck = list(range(len(SASTA_EVENTS)))
        random.shuffle(game.event_deck)
        game.used_event_deck = []

    def _ensure_deck_capacity(self, game: GameSession, count: int = 3) -> None:
        """Ensure deck has enough cards by reshuffling discard if needed."""
        if len(game.event_deck) < count:
            if game.used_event_deck:
                game.event_deck.extend(game.used_event_deck)
                game.used_event_deck = []
                # Only shuffle the NEWLY added part? Or whole?
                # Usually standard deck: shuffle discard, put under?
                # Or shuffle whole remaining?
                # Let's shuffle whole deck to be safe and simple.
                random.shuffle(game.event_deck)

    def _draw_event(self, game: GameSession) -> Optional[dict]:
        """Draw next event from deck."""
        if not game.event_deck:
            self._ensure_deck_capacity(game, 1)
        
        if not game.event_deck:
            return None

        event_idx = game.event_deck.pop(0)
        game.used_event_deck.append(event_idx)
        return SASTA_EVENTS[event_idx]

    def _calculate_go_bonus(self, game: GameSession) -> int:
        """Calculate GO bonus with inflation using game settings."""
        base = game.settings.go_bonus_base
        inflation = game.current_round * game.settings.go_inflation_per_round
        return base + inflation

    def _owns_full_set(self, player: Player, color: str, board: list[Tile]) -> bool:
        """Check if player owns all properties of a color."""
        if not color:
            return False
        color_tiles = [t for t in board if t.type == TileType.PROPERTY and t.color == color]
        if not color_tiles:
            return False
        return all(t.owner_id == player.id for t in color_tiles)

    def _calculate_rent(self, tile: Tile, owner: Player, game: GameSession) -> int:
        """Calculate rent with set bonus and upgrades."""
        if tile.type != TileType.PROPERTY:
            return 0
        
        base_rent = tile.rent
        
        if self._owns_full_set(owner, tile.color, game.board):
            base_rent *= 2
        
        if tile.upgrade_level == 1:
            base_rent = int(base_rent * 1.5)  # Script Kiddie: +50%
        elif tile.upgrade_level == 2:
            base_rent = int(base_rent * 3.0)  # 1337 Haxxor: +200%
        
        base_rent = int(base_rent * game.rent_multiplier)
        
        if tile.blocked_until_round and tile.blocked_until_round > game.current_round:
            return 0

        if tile.id in game.blocked_tiles:
            return 0
        
        return base_rent

    async def _send_to_jail(self, game: GameSession, player: Player) -> None:
        """Send player to Server Downtime (jail)."""
        jail_pos = len(game.board) // 2
        player.position = jail_pos
        player.in_jail = True
        player.jail_turns = 0
        await self.repository.update_player_position(player.id, jail_pos)
        game.last_event_message = f"🚨 {player.name} sent to SERVER DOWNTIME!"

    async def _play_cpu_turn(self, game: GameSession, cpu_player: Player) -> list[str]:
        """Play a full CPU turn until turn is complete, return log of actions."""
        turn_log = []
        max_iterations = 20  # Safety limit to prevent infinite loops
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            game = await self.get_game(game.id)
            
            if game.current_turn_player_id != cpu_player.id:
                turn_log.append(f"{cpu_player.name} turn ended (not their turn anymore)")
                break

            cpu_player = next((p for p in game.players if p.id == cpu_player.id), cpu_player)
            if not cpu_player:
                turn_log.append(f"{cpu_player.name} not found in game")
                break

            if game.turn_phase == TurnPhase.PRE_ROLL:
                roll_result = await self.perform_action(game.id, cpu_player.id, ActionType.ROLL_DICE, None)
                if roll_result.success:
                    turn_log.append(f"{cpu_player.name} rolled: {roll_result.message}")
                else:
                    turn_log.append(f"{cpu_player.name} failed to roll: {roll_result.message}")
                    break
                continue

            if game.turn_phase == TurnPhase.DECISION:
                if game.pending_decision:
                    decision = game.pending_decision
                    
                    if decision.type == "BUY":
                        tile_cost = decision.price
                        if cpu_player.cash >= tile_cost + 200:
                            result = await self.perform_action(game.id, cpu_player.id, ActionType.BUY_PROPERTY, None)
                            if result.success:
                                turn_log.append(f"{cpu_player.name} bought property: {result.message}")
                            else:
                                result = await self.perform_action(game.id, cpu_player.id, ActionType.PASS_PROPERTY, None)
                                turn_log.append(f"{cpu_player.name} passed (buy failed: {result.message})")
                        else:
                            result = await self.perform_action(game.id, cpu_player.id, ActionType.PASS_PROPERTY, None)
                            turn_log.append(f"{cpu_player.name} passed on property (insufficient funds)")
                    elif decision.type == "MARKET" or decision.type == "BLACK_MARKET":
                        # CPU logic: Always skip for now
                        result = await self.perform_action(game.id, cpu_player.id, ActionType.PASS_PROPERTY, None)
                        turn_log.append(f"{cpu_player.name} left Black Market")
                    else:
                        result = await self.perform_action(game.id, cpu_player.id, ActionType.PASS_PROPERTY, None)
                        turn_log.append(f"{cpu_player.name} passed on decision type: {decision.type}")
                else:
                    turn_log.append(f"{cpu_player.name} in DECISION phase but no pending decision - transitioning to POST_TURN")
                    game = await self.get_game(game.id)
                    game.turn_phase = TurnPhase.POST_TURN
                    game.pending_decision = None
                    await self.repository.update(game)
                continue

            if game.turn_phase == TurnPhase.POST_TURN:
                result = await self.perform_action(game.id, cpu_player.id, ActionType.END_TURN, None)
                if result.success:
                    turn_log.append(f"{cpu_player.name} ended turn")
                    break
                else:
                    turn_log.append(f"{cpu_player.name} failed to end turn: {result.message}")
                    break

            if game.turn_phase == TurnPhase.AUCTION:
                turn_log.append(f"{cpu_player.name} pausing turn for Auction")
                break

            if game.turn_phase == TurnPhase.MOVING:
                continue

            turn_log.append(f"{cpu_player.name} stuck in unexpected phase: {game.turn_phase.value}")
            break

        if iterations >= max_iterations:
            turn_log.append(f"{cpu_player.name} hit max iterations limit ({max_iterations})")

        return turn_log

    async def process_cpu_turns(self, game_id: str) -> dict:
        """Process all consecutive CPU turns until a human player's turn."""
        game = await self.get_game(game_id)
        all_logs = []
        max_cpu_turns = 10  # Safety limit
        turns_played = 0

        while game.status == GameStatus.ACTIVE and turns_played < max_cpu_turns:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player or not self._is_cpu_player(current_player):
                break  # Human player's turn

            turn_log = await self._play_cpu_turn(game, current_player)
            all_logs.extend(turn_log)
            turns_played += 1
            game = await self.get_game(game_id)

        return {"cpu_turns_played": turns_played, "log": all_logs}

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

        game.starting_cash = game_config.starting_cash
        game.go_bonus = game_config.go_bonus

        self._initialize_event_deck(game)

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
            go_bonus = self._calculate_go_bonus(game)
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
            go_bonus = self._calculate_go_bonus(game)
            game.last_event_message = f"Welcome to GO! Collect ${go_bonus} when you pass."
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.PROPERTY:
            if tile.owner_id is None:
                game.pending_decision = PendingDecision(
                    type="BUY",
                    tile_id=tile.id,
                    price=tile.price,
                )
                color_info = f" [{tile.color}]" if tile.color else ""
                game.last_event_message = f"'{tile.name}'{color_info} is for sale! Price: ${tile.price}"

            elif tile.owner_id == player.id:
                game.last_event_message = f"You own '{tile.name}'. Safe!"
                game.turn_phase = TurnPhase.POST_TURN

            else:
                owner = next((p for p in game.players if p.id == tile.owner_id), None)
                if owner:
                    rent = self._calculate_rent(tile, owner, game)
                    
                    if player.active_buff == "VPN":
                        player.active_buff = None
                        game.last_event_message = f"🛡️ VPN activated! Blocked ${rent} rent to {owner.name}!"
                    else:
                        await self._charge_player(game, player, rent, owner)
                        if not player.is_bankrupt:
                            bonus_info = ""
                            if self._owns_full_set(owner, tile.color, game.board):
                                bonus_info = " (SET BONUS!)"
                            if tile.upgrade_level > 0:
                                level_name = "SCRIPT KIDDIE" if tile.upgrade_level == 1 else "1337 HAXXOR"
                                bonus_info += f" [{level_name}]"
                            
                            game.last_event_message = f"💸 Paid ${rent} rent to {owner.name}{bonus_info}"
                game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.CHANCE:
            event = await self._handle_sasta_event(game, player, tile)
            game.last_event_message = f"🎲 {event['name']}: {event['desc']}"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.TAX:
            go_bonus = self._calculate_go_bonus(game)
            tax_amount = tile.price if tile.price > 0 else go_bonus // 2
            await self._charge_player(game, player, tax_amount)
            if not player.is_bankrupt:
                game.last_event_message = f"💸 Paid ${tax_amount} in taxes for '{tile.name}'"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.BUFF:
            go_bonus = self._calculate_go_bonus(game)
            buff_amount = go_bonus // 2
            player.cash += buff_amount
            await self.repository.update_player_cash(player.id, player.cash)
            game.last_event_message = f"🎁 Received ${buff_amount} from '{tile.name}'!"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.TRAP:
            go_bonus = self._calculate_go_bonus(game)
            trap_amount = go_bonus // 3
            await self._charge_player(game, player, trap_amount)
            if not player.is_bankrupt:
                game.last_event_message = f"⚠️ Lost ${trap_amount} from '{tile.name}'!"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.NEUTRAL:
            game.last_event_message = f"Landed on '{tile.name}'. Nothing happens."
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.JAIL:
            game.last_event_message = f"👀 Just visiting SERVER DOWNTIME. Stay safe!"
            game.turn_phase = TurnPhase.POST_TURN

        elif tile.type == TileType.TELEPORT:
            await self._handle_glitch(game, player)



        elif tile.type == TileType.MARKET:
            game.pending_decision = PendingDecision(
                type="MARKET",
                event_data={
                    "buffs": [
                        {"id": "VPN", "name": "VPN (Immunity)", "cost": 200, "desc": "Block next rent"},
                        {"id": "DDOS", "name": "DDoS (Blockade)", "cost": 150, "desc": "Disable a tile"},
                        {"id": "PEEK", "name": "Insider Info", "cost": 100, "desc": "See next 3 events"},
                    ]
                }
            )
            game.last_event_message = f"🛒 Welcome to the BLACK MARKET! Buy a buff."

        else:
            game.turn_phase = TurnPhase.POST_TURN

    async def _handle_glitch(self, game: GameSession, player: Player) -> None:
        """Handle The Glitch tile: teleport to random unowned property."""
        unowned = [t for t in game.board if t.type == TileType.PROPERTY and not t.owner_id]
        
        if unowned:
            target = random.choice(unowned)
        else:
            events = [t for t in game.board if t.type == TileType.CHANCE]
            target = random.choice(events) if events else game.board[0]
        
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
        event = self._draw_event(game)
        if not event:
             # Fallback if config broken
             event = random.choice(SASTA_EVENTS)

        if event["type"] == "CASH_GAIN":
            player.cash += event["value"]
            await self.repository.update_player_cash(player.id, player.cash)

        elif event["type"] == "CASH_LOSS":
            await self._charge_player(game, player, event["value"])

        elif event["type"] == "COLLECT_FROM_ALL":
            for p in game.players:
                if p.id != player.id:
                    await self._charge_player(game, p, event["value"], player)

        elif event["type"] == "SKIP_BUY":
            game.pending_decision = None

        elif event["type"] == "MOVE_BACK":
            new_pos = max(0, player.position - event["value"])
            await self.repository.update_player_position(player.id, new_pos)
            player.position = new_pos

        return event

    async def perform_action(
        self, game_id: str, player_id: str, action_type: ActionType, payload: dict
    ) -> ActionResult:
        """Perform a game action."""
        game = await self.get_game(game_id)

        if action_type == ActionType.ROLL_DICE:
            try:
                dice_result = await self.roll_dice(game_id, player_id)
                updated_game = await self.get_game(game_id)
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

            player.cash -= price
            player.properties.append(tile_id)
            await self.repository.update_player_cash(player_id, player.cash)
            await self.repository.update_player_properties(player_id, player.properties)
            await self.repository.update_tile_owner(tile_id, player_id)

            tile = next((t for t in game.board if t.id == tile_id), None)
            tile_name = tile.name if tile else "property"

            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            game.last_event_message = f"🏠 Bought '{tile_name}' for ${price}!"
            await self.repository.update(game)

            return ActionResult(success=True, message=f"Bought '{tile_name}' for ${price}")

        elif action_type == ActionType.PASS_PROPERTY:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Not your turn")

            if game.turn_phase != TurnPhase.DECISION:
                return ActionResult(success=False, message="Cannot pass now")
            
            if game.settings.enable_auctions and game.pending_decision and game.pending_decision.type == "BUY":
                tile_id = game.pending_decision.tile_id
                tile = next((t for t in game.board if t.id == tile_id), None)
                
                if tile and tile.type == TileType.PROPERTY and not tile.owner_id:
                    game.turn_phase = TurnPhase.AUCTION
                    auction_duration = 30
                    
                    participants = [p.id for p in game.players if not p.is_bankrupt]
                    
                    game.auction_state = AuctionState(
                        property_id=tile_id,
                        highest_bid=0,
                        highest_bidder_id=None,
                        start_time=time.time(),
                        end_time=time.time() + auction_duration,
                        participants=participants,
                        min_bid_increment=10
                    )
                    game.last_event_message = f"🔨 Auction started for {tile.name}!"
                    game.pending_decision = None
                    
                    await self.repository.update(game)
                    return ActionResult(success=True, message=f"Auction started for {tile.name}")

            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            game.last_event_message = "Passed on decision."
            await self.repository.update(game)

            return ActionResult(success=True, message="Passed on decision")

        elif action_type == ActionType.BID:
            if game.turn_phase != TurnPhase.AUCTION or not game.auction_state:
                return ActionResult(success=False, message="No active auction")
            
            amount = payload.get("amount")
            if not amount:
                return ActionResult(success=False, message="Bid amount required")
            
            if time.time() > game.auction_state.end_time:
                 return await self._resolve_auction(game)

            min_bid = game.auction_state.highest_bid + game.auction_state.min_bid_increment
            if amount < min_bid:
                return ActionResult(success=False, message=f"Bid too low. Min: {min_bid}")
            
            player = next((p for p in game.players if p.id == player_id), None)
            if not player or player.cash < amount:
                 return ActionResult(success=False, message="Insufficient funds")

            if player_id not in game.auction_state.participants:
                 return ActionResult(success=False, message="Not a participant")

            game.auction_state.highest_bid = amount
            game.auction_state.highest_bidder_id = player_id
            
            remaining = game.auction_state.end_time - time.time()
            if remaining < 5:
                game.auction_state.end_time = time.time() + 5
                game.last_event_message = f"🔨 {player.name} bid ${amount}! Timer extended!"
            else:
                game.last_event_message = f"🔨 {player.name} bid ${amount}!"

            
            await self.repository.update(game)
            return ActionResult(success=True, message=f"Bid accepted: ${amount}")
            
        elif action_type == ActionType.RESOLVE_AUCTION:
             return await self._resolve_auction(game)

        elif action_type == ActionType.UPGRADE:
            tile_id = payload.get("tile_id")
            if not tile_id:
                return ActionResult(success=False, message="Tile ID required")
            
            tile = next((t for t in game.board if t.id == tile_id), None)
            if not tile or tile.type != TileType.PROPERTY:
                return ActionResult(success=False, message="Invalid property")

            if tile.owner_id != player_id:
                return ActionResult(success=False, message="You don't own this property")

            player = next(p for p in game.players if p.id == player_id)
            if not self._owns_full_set(player, tile.color, game.board):
                 return ActionResult(success=False, message="You must own the full color set to upgrade")

            if tile.upgrade_level >= 2:
                 return ActionResult(success=False, message="Max upgrade level reached")
            
            # Cost: Level 1 = Price, Level 2 = Price * 2
            upgrade_cost = tile.price * (2 if tile.upgrade_level == 1 else 1)
            
            if player.cash < upgrade_cost:
                 return ActionResult(success=False, message=f"Insufficient funds (Need ${upgrade_cost})")

            player.cash -= upgrade_cost
            tile.upgrade_level += 1
            
            level_name = "SCRIPT KIDDIE" if tile.upgrade_level == 1 else "1337 HAXXOR"
            game.last_event_message = f"💻 {player.name} upgraded {tile.name} to {level_name}!"
            
            await self.repository.update_player_cash(player.id, player.cash)
            await self.repository.save_board(game.id, game.board)
            await self.repository.update(game)
            
            return ActionResult(success=True, message=f"Upgraded to {level_name}")
        elif action_type == ActionType.BUY_BUFF:
            if game.turn_phase != TurnPhase.DECISION or not game.pending_decision or game.pending_decision.type != "MARKET":
                 return ActionResult(success=False, message="Not in Market")

            buff_id = payload.get("buff_id")
            buffs = game.pending_decision.event_data.get("buffs", [])
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
                preview_names = [SASTA_EVENTS[idx]["name"] for idx in preview_indices]
                
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

        elif action_type == ActionType.BLOCK_TILE:
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

        elif action_type == ActionType.PROPOSE_TRADE:
            if game.current_turn_player_id != player_id:
                return ActionResult(success=False, message="Can only propose trades on your turn")
            
            target_id = payload.get("target_id")
            if not target_id or target_id == player_id:
                return ActionResult(success=False, message="Invalid trade target")
            
            target_player = next((p for p in game.players if p.id == target_id), None)
            if not target_player:
                return ActionResult(success=False, message="Target player not found")

            offer_cash = int(payload.get("offer_cash", 0))
            req_cash = int(payload.get("req_cash", 0))
            offer_props = payload.get("offer_props", [])
            req_props = payload.get("req_props", [])

            if offer_cash < 0 or req_cash < 0:
                 return ActionResult(success=False, message="Negative cash invalid")

            # Validate Initiator Assets
            if player.cash < offer_cash:
                return ActionResult(success=False, message="Insufficient cash for offer")
            
            for pid in offer_props:
                tile = next((t for t in game.board if t.id == pid), None)
                if not tile or tile.owner_id != player_id:
                    return ActionResult(success=False, message=f"You don't own property {pid}")

            # Validate Target Assets (Properties only, cash check pending acceptance)
            for pid in req_props:
                tile = next((t for t in game.board if t.id == pid), None)
                if not tile or tile.owner_id != target_id:
                    return ActionResult(success=False, message=f"Target doesn't own property {pid}")

            offer = TradeOffer(
                initiator_id=player_id,
                target_id=target_id,
                offering_cash=offer_cash,
                offering_properties=offer_props,
                requesting_cash=req_cash,
                requesting_properties=req_props,
                created_at=time.time()
            )
            game.active_trade_offers.append(offer)
            game.last_event_message = f"🤝 {player.name} proposed a trade to {target_player.name}!"
            await self.repository.update(game)
            return ActionResult(success=True, message="Trade offered")

        elif action_type == ActionType.ACCEPT_TRADE:
            trade_id = payload.get("trade_id")
            offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
            if not offer:
                return ActionResult(success=False, message="Trade offer not found")
            
            if offer.target_id != player_id:
                return ActionResult(success=False, message="Not authorized to accept this trade")

            initiator = next((p for p in game.players if p.id == offer.initiator_id), None)
            if not initiator:
                game.active_trade_offers.remove(offer) # Cleanup
                await self.repository.update(game)
                return ActionResult(success=False, message="Initiator gone")

            # Re-Validate Assets (State might have changed)
            if initiator.cash < offer.offering_cash:
                 return ActionResult(success=False, message="Initiator cannot afford trade anymore")
            if player.cash < offer.requesting_cash:
                 return ActionResult(success=False, message="You cannot afford trade")

            # Validate Properties Ownership
            for pid in offer.offering_properties:
                tile = next((t for t in game.board if t.id == pid), None)
                if not tile or tile.owner_id != initiator.id:
                    return ActionResult(success=False, message="Initiator lost offer properties")
            
            for pid in offer.requesting_properties:
                tile = next((t for t in game.board if t.id == pid), None)
                if not tile or tile.owner_id != player.id:
                    return ActionResult(success=False, message="You lost requested properties")

            # Execute Transfer
            initiator.cash -= offer.offering_cash
            initiator.cash += offer.requesting_cash
            player.cash += offer.offering_cash
            player.cash -= offer.requesting_cash
            
            await self.repository.update_player_cash(initiator.id, initiator.cash)
            await self.repository.update_player_cash(player.id, player.cash)

            # Properties
            for pid in offer.offering_properties:
                tile = next((t for t in game.board if t.id == pid), None)
                tile.owner_id = player.id
            
            for pid in offer.requesting_properties:
                tile = next((t for t in game.board if t.id == pid), None)
                tile.owner_id = initiator.id
            
            await self.repository.save_board(game.id, game.board)

            # Cleanup
            game.active_trade_offers.remove(offer)
            game.last_event_message = f"🤝 Trade accepted between {initiator.name} and {player.name}!"
            await self.repository.update(game)
            return ActionResult(success=True, message="Trade completed")

        elif action_type == ActionType.DECLINE_TRADE:
            trade_id = payload.get("trade_id")
            offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
            if not offer:
                return ActionResult(success=False, message="Trade not found")
            
            if offer.target_id != player_id:
                return ActionResult(success=False, message="Not authorized")
            
            game.active_trade_offers.remove(offer)
            game.last_event_message = f"🚫 {player.name} declined trade."
            await self.repository.update(game)
            return ActionResult(success=True, message="Declined")

        elif action_type == ActionType.CANCEL_TRADE:
            trade_id = payload.get("trade_id")
            offer = next((t for t in game.active_trade_offers if t.id == trade_id), None)
            if not offer:
                return ActionResult(success=False, message="Trade not found")
            
            if offer.initiator_id != player_id:
                 return ActionResult(success=False, message="Not authorized")

            game.active_trade_offers.remove(offer)
            await self.repository.update(game)
            return ActionResult(success=True, message="Cancelled")



        elif action_type == ActionType.END_TURN:
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

            if await self._check_and_handle_end_conditions(game_id):
                game = await self.get_game(game_id)
                winner = self._determine_winner(game)
                return ActionResult(
                    success=True,
                    message=f"🏆 Game Over! {winner['name']} wins!",
                    data={"game_over": True, "winner": winner}
                )

            game = await self.get_game(game_id)
            
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
                
                # Clear blocked tiles when round advances
                for tile in game.board:
                    if tile.blocked_until_round and tile.blocked_until_round <= game.current_round:
                        tile.blocked_until_round = None
                
                if (game.settings.win_condition == WinCondition.SUDDEN_DEATH and 
                    game.settings.round_limit > 0 and
                    game.current_round >= game.settings.round_limit):
                    winner = self._determine_winner(game)
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

            # Save board if round changed (to persist cleared blocked_until_round)
            if game.current_round > old_round:
                await self.repository.save_board(game.id, game.board)

            await self.repository.update(game)

            round_limit_display = game.settings.round_limit if game.settings.round_limit > 0 else "∞"
            round_info = f" [Round {game.current_round}/{round_limit_display}]"
            return ActionResult(success=True, message=f"Turn ended. {next_player.name}'s turn!{round_info}")

        else:
            return ActionResult(success=False, message=f"Unknown action: {action_type}")

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
        stuck_counter = 0  # Detect infinite loops
        last_state = None
        
        while turns_played < max_turns and game.status == GameStatus.ACTIVE:
            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player:
                break
            
            # Detect stuck state
            current_state = f"{game.turn_phase.value}:{current_player.id}:{game.pending_decision}"
            if current_state == last_state:
                stuck_counter += 1
                if stuck_counter > 5:
                    # Force transition out of stuck state
                    game.turn_phase = TurnPhase.POST_TURN
                    game.pending_decision = None
                    await self.repository.update(game)
                    stuck_counter = 0
            else:
                stuck_counter = 0
                last_state = current_state
            
            turn_info = {
                "turn": turns_played + 1,
                "round": game.current_round,
                "player": current_player.name,
                "player_id": current_player.id,
                "cash_before": current_player.cash,
                "position_before": current_player.position,
                "in_jail": current_player.in_jail,
                "actions": [],
            }
            
            if game.turn_phase == TurnPhase.PRE_ROLL:
                result = await self.perform_action(game_id, current_player.id, ActionType.ROLL_DICE, {})
                turn_info["actions"].append({"action": "ROLL_DICE", "result": result.message})
                game = await self.get_game(game_id)
            
            if game.turn_phase == TurnPhase.DECISION and game.pending_decision:
                current_player = next(
                    (p for p in game.players if p.id == game.current_turn_player_id), None
                )
                decision_type = game.pending_decision.type
                
                if decision_type == "BUY":
                    price = game.pending_decision.price
                    if current_player and current_player.cash >= price * 1.5:
                        result = await self.perform_action(game_id, current_player.id, ActionType.BUY_PROPERTY, {})
                        turn_info["actions"].append({"action": "BUY_PROPERTY", "result": result.message})
                    else:
                        result = await self.perform_action(game_id, current_player.id, ActionType.PASS_PROPERTY, {})
                        turn_info["actions"].append({"action": "PASS_PROPERTY", "result": result.message})
                    game = await self.get_game(game_id)
                
                elif decision_type == "MARKET":
                    buffs = game.pending_decision.event_data.get("buffs", []) if game.pending_decision.event_data else []
                    bought = False
                    
                    if current_player and not current_player.active_buff:
                        for buff in buffs:
                            if current_player.cash >= buff["cost"] + 300:
                                result = await self.perform_action(game_id, current_player.id, ActionType.BUY_BUFF, {"buff_id": buff["id"]})
                                turn_info["actions"].append({"action": "BUY_BUFF", "result": result.message})
                                bought = True
                                break
                    
                    if not bought:
                        result = await self.perform_action(game_id, current_player.id, ActionType.PASS_PROPERTY, {})
                        turn_info["actions"].append({"action": "PASS_MARKET", "result": result.message})
                    
                    game = await self.get_game(game_id)

                
                else:
                    turn_info["actions"].append({"action": f"SKIP_{decision_type}", "result": f"Skipped unknown decision: {decision_type}"})
                    game.pending_decision = None
                    game.turn_phase = TurnPhase.POST_TURN
                    await self.repository.update(game)
            
            if game.turn_phase == TurnPhase.POST_TURN:
                result = await self.perform_action(game_id, current_player.id, ActionType.END_TURN, {})
                turn_info["actions"].append({"action": "END_TURN", "result": result.message})
                game = await self.get_game(game_id)
                
                if result.data and result.data.get("game_over"):
                    turn_info["actions"].append({"action": "GAME_OVER", "result": result.message})
                    break
            
            current_player = next(
                (p for p in game.players if p.id == turn_info["player_id"]), None
            )
            if current_player:
                turn_info["cash_after"] = current_player.cash
                turn_info["position_after"] = current_player.position
            
            turn_log.append(turn_info)
            turns_played += 1
            
            game = await self._check_bankruptcy(game_id)
            active_players = [p for p in game.players if not p.is_bankrupt and p.cash >= 0]
            if len(active_players) <= 1:
                game.status = GameStatus.FINISHED
                await self.repository.update(game)
                break
        
        game = await self.get_game(game_id)
        
        return {
            "game_id": game_id,
            "status": game.status.value,
            "turns_played": turns_played,
            "rounds_played": game.current_round,
            "max_rounds": game.max_rounds,
            "winner": self._determine_winner(game),
            "final_standings": [
                {"name": p.name, "cash": p.cash, "properties": len(p.properties), "bankrupt": p.is_bankrupt}
                for p in sorted(game.players, key=lambda x: x.cash, reverse=True)
            ],
            "turn_log": turn_log[-10:],  # Last 10 turns only
        }
    
    async def _resolve_auction(self, game: GameSession) -> ActionResult:
        """Resolve a finished auction."""
        if not game.auction_state:
            return ActionResult(success=False, message="No auction state")
        
        state = game.auction_state
        winner_id = state.highest_bidder_id
        amount = state.highest_bid
        prop_id = state.property_id
        
        tile = next((t for t in game.board if t.id == prop_id), None)
        tile_name = tile.name if tile else "Property"
        
        if winner_id:
            winner = next((p for p in game.players if p.id == winner_id), None)
            if winner:
                winner.cash -= amount
                winner.properties.append(prop_id)
                await self.repository.update_player_cash(winner.id, winner.cash)
                await self.repository.update_player_properties(winner.id, winner.properties)
                await self.repository.update_tile_owner(prop_id, winner.id)
                
                game.last_event_message = f"🔨 SOLD! {tile_name} to {winner.name} for ${amount}!"
        else:
            game.last_event_message = f"🔨 Auction ended. No bids for {tile_name}."
            
        game.auction_state = None
        game.turn_phase = TurnPhase.POST_TURN
        await self.repository.update(game)
        
        return ActionResult(success=True, message=game.last_event_message)

    async def _auto_liquidate(self, game: GameSession, player: Player, needed: int) -> int:
        """Attempt to raise cash by downgrading/selling assets (Fire Sale)."""
        raised = 0
        
        upgraded_tiles = [t for t in game.board if t.owner_id == player.id and t.upgrade_level > 0]
        upgraded_tiles.sort(key=lambda x: x.upgrade_level, reverse=True)
        
        for tile in upgraded_tiles:
            while tile.upgrade_level > 0 and raised < needed:
                refund = tile.price if tile.upgrade_level == 2 else tile.price // 2
                tile.upgrade_level -= 1
                player.cash += refund
                raised += refund
                
                if raised >= needed:
                    break
        
        if raised >= needed:
            await self.repository.save_board(game.id, game.board)
            return raised

        properties = [t for t in game.board if t.owner_id == player.id]
        properties.sort(key=lambda x: x.price)
        
        for tile in properties:
            if raised >= needed:
                break
                
            sell_value = tile.price // 2
            if tile.upgrade_level == 2:
                extra_refund = tile.price + (tile.price // 2)
            elif tile.upgrade_level == 1:
                extra_refund = tile.price // 2
            else:
                extra_refund = 0
                
            player.cash += sell_value + extra_refund
            raised += sell_value + extra_refund
            tile.owner_id = None
            tile.upgrade_level = 0
            
        await self.repository.save_board(game.id, game.board)
        return raised

    async def _process_bankruptcy(self, game: GameSession, debtor: Player, creditor: Player = None):
        """Handle bankruptcy: asset transfer or seizure."""
        debtor.is_bankrupt = True
        remaining_cash = max(0, debtor.cash)
        debtor.cash = 0
        
        debtor_properties = [t for t in game.board if t.owner_id == debtor.id]
        
        if creditor:
            for tile in debtor_properties:
                tile.owner_id = creditor.id
            creditor.cash += remaining_cash
            await self.repository.update_player_cash(creditor.id, creditor.cash)
            game.last_event_message = f"💀 {debtor.name} went BANKRUPT! Assets seized by {creditor.name}."
        else:
            for tile in debtor_properties:
                tile.owner_id = None
                tile.upgrade_level = 0
            game.last_event_message = f"💀 {debtor.name} went BANKRUPT! Assets seized by Bank."

        await self.repository.update_player_bankrupt(debtor.id, True)
        await self.repository.update_player_cash(debtor.id, 0)
        await self.repository.save_board(game.id, game.board)

    async def _charge_player(self, game: GameSession, player: Player, amount: int, creditor: Player = None):
        """Charge a player amount. Trigger Fire Sale or Bankruptcy if needed."""
        if amount <= 0:
            return

        if player.cash >= amount:
            player.cash -= amount
            if creditor:
                creditor.cash += amount
                await self.repository.update_player_cash(creditor.id, creditor.cash)
            await self.repository.update_player_cash(player.id, player.cash)
            return

        needed = amount - player.cash
        game.last_event_message = (game.last_event_message or "") + " | 📉 FIRE SALE triggered!"
        raised = await self._auto_liquidate(game, player, needed)
        
        if player.cash + raised >= amount:
            player.cash -= amount
            if creditor:
                creditor.cash += amount
                await self.repository.update_player_cash(creditor.id, creditor.cash)
            await self.repository.update_player_cash(player.id, player.cash)
            game.last_event_message = (game.last_event_message or "") + f" | Survived by selling assets."
        else:
            await self._process_bankruptcy(game, player, creditor)

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
            
            # Force action based on phase
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
        active_players = [p for p in game.players if p.cash >= 0]
        
        if len(active_players) == 1:
            winner = active_players[0]
            return {"name": winner.name, "cash": winner.cash, "properties": len(winner.properties)}
        elif len(active_players) == 0:
            richest = max(game.players, key=lambda x: x.cash)
            return {"name": richest.name, "cash": richest.cash, "properties": len(richest.properties)}
        else:
            leader = max(active_players, key=lambda x: x.cash)
            return {"name": leader.name, "cash": leader.cash, "properties": len(leader.properties), "status": "in_progress"}
