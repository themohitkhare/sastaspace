"""Game orchestrator - thin coordinator delegating to managers."""

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.sastadice.events.event_manager import EventManager
from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.schemas import (
    ActionResult,
    ActionType,
    ChaosConfig,
    DiceRollResult,
    GameSession,
    GameStatus,
    Player,
    Tile,
    TileCreate,
    TileType,
    TurnPhase,
)
from app.modules.sastadice.services.action_dispatcher import ActionDispatcher
from app.modules.sastadice.services.auction_manager import AuctionManager
from app.modules.sastadice.services.board_generation_service import BoardGenerationService
from app.modules.sastadice.services.cpu_manager import CpuManager
from app.modules.sastadice.services.economy_manager import EconomyManager
from app.modules.sastadice.services.jail_manager import JailManager
from app.modules.sastadice.services.lobby_manager import LobbyManager
from app.modules.sastadice.services.simulation_manager import SimulationManager
from app.modules.sastadice.services.trade_manager import TradeManager
from app.modules.sastadice.services.turn_coordinator import TurnCoordinator
from app.modules.sastadice.services.turn_manager import TurnManager


class GameOrchestrator:
    """Single entry point for all game operations. Coordinates managers."""

    def __init__(self, database: "AsyncIOMotorDatabase[Any]") -> None:
        """Initialize game orchestrator with all managers."""
        self.repository = GameRepository(database)
        self.repository.set_on_update(self._broadcast_state)
        self.board_service = BoardGenerationService()
        self.turn_manager = TurnManager()
        self.turn_coordinator = TurnCoordinator(self.repository, self.turn_manager)
        self.auction_manager = AuctionManager()
        self.trade_manager = TradeManager()
        self.economy_manager = EconomyManager(self.repository)
        self.jail_manager = JailManager()
        self.event_manager = EventManager(self.repository)

        self.lobby_manager = LobbyManager(self.repository, self.board_service, self.turn_manager)
        self.action_dispatcher = ActionDispatcher(
            self.repository,
            self.economy_manager,
            self.auction_manager,
            self.trade_manager,
            self.turn_coordinator,
            self.turn_manager,
            self.jail_manager,
            roll_dice_callback=self.roll_dice,
            handle_tile_landing_callback=self._handle_tile_landing,
            send_to_jail_callback=self._send_to_jail,
        )

        # Simulation manager (will be initialized after action_dispatcher)
        self.simulation_manager = None

        # CPU manager (needs orchestrator reference for now - will refactor later)
        self.cpu_manager = CpuManager(self)

    async def _broadcast_state(self, game_id: str) -> None:
        """Broadcast current game state to all WebSocket connections."""
        from app.modules.sastadice.websocket import connection_manager

        try:
            game = await self.get_game(game_id)
            if game:
                version = await self.repository.get_version(game_id)
                await connection_manager.broadcast(
                    game_id,
                    {
                        "type": "STATE_UPDATE",
                        "version": version,
                        "game": game.model_dump(mode="json"),
                    },
                )
        except Exception:
            pass  # Don't let WS errors break game logic

    def _is_cpu_player(self, player: Player) -> bool:
        """Check if a player is a CPU."""
        return self.cpu_manager.is_cpu_player(player)

    async def _send_to_jail(self, game: GameSession, player: Player) -> None:
        """Send player to Server Downtime (jail)."""
        jail_pos = len(game.board) // 2
        player.position = jail_pos
        player.in_jail = True
        player.jail_turns = 0
        await self.repository.update_player_position(player.id, jail_pos)
        game.last_event_message = f"🚨 {player.name} sent to SERVER DOWNTIME!"

    async def _handle_tile_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle what happens when a player lands on a tile."""
        if tile.type == TileType.GO:
            self.turn_manager.handle_go_landing(game, tile)
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
            self.turn_manager.handle_market_landing(game)
        elif tile.type == TileType.GO_TO_JAIL:
            await self._send_to_jail(game, player)
            player.consecutive_doubles = 0
        elif tile.type == TileType.NODE:
            await self._handle_property_landing(game, player, tile)
        else:
            game.last_event_message = f"Landed on '{tile.name}'. Nothing happens."
            game.turn_phase = TurnPhase.POST_TURN

    async def _handle_property_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle property landing."""
        result = self.turn_manager.handle_property_landing(game, player, tile)
        if result.get("action") == "pay_rent":
            await self._handle_owned_property_landing(game, player, tile)

    async def _handle_owned_property_landing(
        self, game: GameSession, player: Player, tile: Tile
    ) -> None:
        """Handle landing on owned property."""
        owner = next((p for p in game.players if p.id == tile.owner_id), None)
        if owner:
            if tile.type == TileType.NODE:
                from app.modules.sastadice.services.node_manager import NodeManager

                rent = NodeManager.calculate_node_rent(owner, game)
            else:
                rent = self.turn_manager.calculate_rent(tile, owner, game)

            if getattr(owner, "double_rent_next_turn", False):
                rent *= 2
                owner.double_rent_next_turn = False
                await self.repository.update_player_double_rent_next_turn(owner.id, False)

            if player.active_buff == "VPN":
                player.active_buff = None
                await self.repository.update_player_buff(player.id, None)
                game.last_event_message = f"🛡️ VPN activated! Blocked ${rent} rent to {owner.name}!"
            else:
                await self._charge_player(game, player, rent, owner)
                if not player.is_bankrupt:
                    bonus_info = ""
                    if tile.color and self.turn_manager.owns_full_set(
                        owner, tile.color, game.board
                    ):
                        bonus_info = " (SET BONUS!)"
                    if tile.upgrade_level > 0:
                        level_name = "SCRIPT KIDDIE" if tile.upgrade_level == 1 else "1337 HAXXOR"
                        bonus_info += f" [{level_name}]"

                    game.last_event_message = f"💸 Paid ${rent} rent to {owner.name}{bonus_info}"
        game.turn_phase = TurnPhase.POST_TURN

    async def _handle_chance_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle chance landing."""
        event = self.turn_manager.handle_chance_landing(game, player, tile)
        actions = await self.event_manager.apply_effect(game, player, event)

        if actions.get("requires_decision"):
            from app.modules.sastadice.schemas import PendingDecision

            game.pending_decision = PendingDecision(
                type=f"EVENT_{actions['special']}", event_data={"event": event, "actions": actions}
            )
            game.last_event_message = f"🎲 {event['name']}: {event['desc']}"
            game.turn_phase = TurnPhase.DECISION
            await self.repository.update(game)
            return

        if actions.get("special") == "MARKET_CRASH":
            game.rent_multiplier = 0.5
        elif actions.get("special") == "BULL_MARKET":
            game.rent_multiplier = 1.5
        elif actions.get("special") == "HYPERINFLATION":
            game.go_bonus_multiplier = 3.0

        if actions.get("skip_buy"):
            game.pending_decision = None

        if actions.get("revealed_player"):
            revealed = actions["revealed_player"]
            game.last_event_message = (
                f"🔍 {event['name']}: {revealed['name']} has ${revealed['cash']}"
            )
        else:
            game.last_event_message = f"🎲 {event['name']}: {event['desc']}"

        game.turn_phase = TurnPhase.POST_TURN

    async def _handle_tax_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle tax landing."""
        tax_amount = self.turn_manager.handle_tax_landing(game, player, tile)
        await self._charge_player(game, player, tax_amount)
        if not player.is_bankrupt:
            game.last_event_message = f"💸 Paid ${tax_amount} in taxes for '{tile.name}'"

    async def _handle_buff_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle buff landing."""
        buff_amount = self.turn_manager.handle_buff_landing(game, player, tile)
        player.cash += buff_amount
        await self.repository.update_player_cash(player.id, player.cash)
        game.last_event_message = f"🎁 Received ${buff_amount} from '{tile.name}'!"

    async def _handle_trap_landing(self, game: GameSession, player: Player, tile: Tile) -> None:
        """Handle trap landing."""
        trap_amount = self.turn_manager.handle_trap_landing(game, player, tile)
        await self._charge_player(game, player, trap_amount)
        if not player.is_bankrupt:
            game.last_event_message = f"⚠️ Lost ${trap_amount} from '{tile.name}'!"

    async def _handle_glitch(self, game: GameSession, player: Player) -> None:
        """Handle The Glitch tile: teleport to random unowned property."""
        target = self.turn_manager.handle_glitch_teleport(game, player)
        if target:
            player.position = target.position
            await self.repository.update_player_position(player.id, target.position)
            game.last_event_message = f"⚡ GLITCH! {player.name} teleported to {target.name}!"

            if target.type in [
                TileType.PROPERTY,
                TileType.CHANCE,
                TileType.TAX,
                TileType.BUFF,
                TileType.NODE,
            ]:
                await self._handle_tile_landing(game, player, target)
            else:
                game.turn_phase = TurnPhase.POST_TURN

    async def _charge_player(
        self, game: GameSession, player: Player, amount: int, creditor: Player | None = None
    ) -> None:
        """Charge a player amount. Trigger Fire Sale or Bankruptcy if needed."""
        result = await self.economy_manager.charge_player(game, player, amount, creditor)

        if result["action"] == "charged":
            return
        elif result["action"] == "charged_after_liquidation":
            game.last_event_message = (
                game.last_event_message or ""
            ) + " | 📉 FIRE SALE triggered! | Survived by selling assets."
        elif result["action"] == "bankrupt":
            game.last_event_message = (game.last_event_message or "") + " | 📉 FIRE SALE triggered!"
            if game.bankruptcy_auction_queue:
                tile = next(
                    (t for t in game.board if t.id == game.bankruptcy_auction_queue[0]),
                    None,
                )
                if tile:
                    self.auction_manager.start_auction(game, tile, auction_duration=10)
                    game.last_event_message = f"🔨 State auction: {tile.name} from bankrupt player!"
                    await self.repository.update(game)

    # Public API methods (delegated to managers)

    async def create_game(self, cpu_count: int = 0) -> GameSession:
        """Create a new game session with optional CPU players."""
        return await self.lobby_manager.create_game(cpu_count)

    async def get_game(self, game_id: str) -> GameSession:
        """Get game session by ID."""
        return await self.lobby_manager.get_game(game_id)

    async def update_settings(
        self, game_id: str, host_id: str, settings_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Update game settings. Only host can update."""
        return await self.lobby_manager.update_settings(game_id, host_id, settings_dict)

    async def join_game(
        self,
        game_id: str,
        player_name: str,
        tiles: list[TileCreate] | None = None,
    ) -> Player:
        """Join a game and submit tiles."""
        return await self.lobby_manager.join_game(game_id, player_name, tiles)

    async def kick_player(
        self, game_id: str, host_id: str, target_player_id: str
    ) -> dict[str, Any]:
        """Kick a player from the game. Only host can kick."""
        return await self.lobby_manager.kick_player(game_id, host_id, target_player_id)

    async def add_cpu_players(self, game_id: str, target_count: int = 2) -> None:
        """Add CPU players to reach target count."""
        return await self.lobby_manager.add_cpu_players(game_id, target_count)

    async def toggle_ready(self, game_id: str, player_id: str) -> dict[str, Any]:
        """Toggle player's launch key. Auto-starts if all players ready."""
        result = await self.lobby_manager.toggle_ready(game_id, player_id)
        if result.get("game_started"):
            await self.start_game(game_id, force=True)
        return result

    async def start_game(self, game_id: str, force: bool = False) -> GameSession:
        """Start a game and generate the board."""
        return await self.lobby_manager.start_game(game_id, force)

    async def roll_dice(self, game_id: str, player_id: str) -> DiceRollResult:
        """Roll dice for a player."""
        game = await self.get_game(game_id)
        return await self.turn_coordinator.roll_dice(
            game, player_id, self._send_to_jail, self._handle_tile_landing
        )

    async def perform_action(
        self,
        game_id: str,
        player_id: str,
        action_type: ActionType,
        payload: dict[str, Any],
    ) -> ActionResult:
        """Dispatch game action to appropriate manager."""
        game = await self.get_game(game_id)
        player = next((p for p in game.players if p.id == player_id), None)
        if player and not self.cpu_manager.is_cpu_player(player):
            await self.repository.update_player_afk(player_id, 0, False, 0)
            player.afk_turns = 0
            player.disconnected = False
            player.disconnected_turns = 0
        return await self.action_dispatcher.dispatch(game, player_id, action_type, payload)

    async def simulate_cpu_game(
        self,
        game_id: str,
        max_turns: int = 100,
        enable_economic_monitoring: bool = False,
        chaos_config: ChaosConfig | None = None,
    ) -> dict[str, Any]:
        simulation_manager = SimulationManager(
            self.repository,
            self.action_dispatcher,
            self.get_game,
            self.start_game,
            enable_economic_monitoring=enable_economic_monitoring,
            chaos_config=chaos_config,
        )
        return await simulation_manager.simulate_cpu_game(game_id, max_turns)

    async def process_cpu_turns(self, game_id: str) -> dict[str, Any]:
        """Process all consecutive CPU turns until a human player's turn."""
        return await self.cpu_manager.process_cpu_turns(game_id)

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
            # Cancel all outstanding trades when a turn times out
            if game.active_trade_offers:
                game.active_trade_offers.clear()
                await self.repository.update(game)

            current_player = next(
                (p for p in game.players if p.id == game.current_turn_player_id), None
            )
            if not current_player:
                return False

            if not self.cpu_manager.is_cpu_player(current_player):
                # Mark player as disconnected; ghost turns will handle AFK counting and bankruptcy.
                await self.repository.update_player_afk(
                    current_player.id,
                    getattr(current_player, "afk_turns", 0),
                    True,
                    disconnected_turns=getattr(current_player, "disconnected_turns", 0),
                )
                current_player.disconnected = True
                game.last_event_message = (
                    f"👻 {current_player.name} AFK! Ghost mode — 3 turns to bankruptcy!"
                )
                await self.repository.update(game)

            if game.turn_phase == TurnPhase.PRE_ROLL:
                await self.perform_action(game_id, current_player.id, ActionType.ROLL_DICE, {})
            elif game.turn_phase == TurnPhase.DECISION:
                await self.perform_action(game_id, current_player.id, ActionType.PASS_PROPERTY, {})
            elif game.turn_phase == TurnPhase.POST_TURN:
                await self.perform_action(game_id, current_player.id, ActionType.END_TURN, {})

            return True

        return False


# Backward compatibility alias
GameService = GameOrchestrator
