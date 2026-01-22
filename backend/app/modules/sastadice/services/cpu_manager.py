"""CPU manager for AI behavior and game simulation."""
import random
from enum import Enum
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import TurnPhase, ActionType, GameStatus, TileType


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


class CpuTurnState(str, Enum):
    """CPU turn state machine states."""

    PRE_ROLL = "PRE_ROLL"
    MOVING = "MOVING"
    DECISION = "DECISION"
    POST_TURN = "POST_TURN"
    AUCTION = "AUCTION"
    COMPLETE = "COMPLETE"


class CpuManager:
    """AI logic for CPU players and game simulation."""

    CPU_NAMES = CPU_NAMES

    def __init__(self, orchestrator: Any):
        """Initialize with orchestrator (forward reference to avoid circular import)."""
        self.orchestrator = orchestrator

    @staticmethod
    def is_cpu_player(player: "Player") -> bool:
        """Check if a player is a CPU."""
        return player.name in CPU_NAMES

    async def cpu_upgrade_properties(
        self, game: "GameSession", cpu_player: "Player", turn_manager
    ) -> bool:
        """CPU attempts to upgrade properties if beneficial. Returns True if upgraded."""
        for tile in game.board:
            if tile.owner_id != cpu_player.id or tile.type != TileType.PROPERTY:
                continue
            if tile.upgrade_level >= 2:
                continue
            if not tile.color or not turn_manager.owns_full_set(
                cpu_player, tile.color, game.board
            ):
                continue

            upgrade_cost = tile.price * (2 if tile.upgrade_level == 1 else 1)
            if cpu_player.cash > upgrade_cost + 300:
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.UPGRADE, {"tile_id": tile.id}
                )
                if result.success:
                    return True
        return False

    async def play_cpu_turn(
        self, game: "GameSession", cpu_player: "Player"
    ) -> list[str]:
        """Play a full CPU turn using state machine pattern."""
        turn_log = []
        max_iterations = 20
        iterations = 0

        state = CpuTurnState(game.turn_phase.value)

        handlers = {
            CpuTurnState.PRE_ROLL: lambda g, p: self._handle_cpu_pre_roll(g, p),
            CpuTurnState.MOVING: lambda g, p: self._handle_cpu_moving(g, p),
            CpuTurnState.DECISION: lambda g, p: self._handle_cpu_decision(g, p),
            CpuTurnState.POST_TURN: lambda g, p: self._handle_cpu_post_turn(g, p),
            CpuTurnState.AUCTION: lambda g, p: self._handle_cpu_auction(g, p),
        }

        while iterations < max_iterations:
            iterations += 1
            game = await self.orchestrator.get_game(game.id)

            if game.current_turn_player_id != cpu_player.id:
                turn_log.append(
                    f"{cpu_player.name} turn ended (not their turn anymore)"
                )
                break

            cpu_player = next(
                (p for p in game.players if p.id == cpu_player.id), cpu_player
            )
            if not cpu_player:
                turn_log.append(f"{cpu_player.name} not found in game")
                break

            handler = handlers.get(state)
            if not handler:
                turn_log.append(
                    f"{cpu_player.name} stuck in unexpected phase: {state.value}"
                )
                break

            new_state, log_entry = await handler(game, cpu_player)
            if log_entry:
                turn_log.append(log_entry)

            if new_state == CpuTurnState.COMPLETE:
                break

            state = new_state

        if iterations >= max_iterations:
            turn_log.append(
                f"{cpu_player.name} hit max iterations limit ({max_iterations})"
            )

        return turn_log

    async def _handle_cpu_pre_roll(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, Optional[str]]:
        """Handle CPU pre-roll phase."""
        roll_result = await self.orchestrator.perform_action(
            game.id, cpu_player.id, ActionType.ROLL_DICE, {}
        )
        if roll_result.success:
            updated_game = await self.orchestrator.get_game(game.id)
            new_state = CpuTurnState(updated_game.turn_phase.value)
            return new_state, f"{cpu_player.name} rolled: {roll_result.message}"
        else:
            return (
                CpuTurnState.COMPLETE,
                f"{cpu_player.name} failed to roll: {roll_result.message}",
            )

    async def _handle_cpu_decision(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, Optional[str]]:
        """Handle CPU decision phase."""
        if not game.pending_decision:
            game = await self.orchestrator.get_game(game.id)
            game.turn_phase = TurnPhase.POST_TURN
            game.pending_decision = None
            await self.orchestrator.repository.update(game)
            return CpuTurnState.POST_TURN, f"{cpu_player.name} in DECISION phase but no pending decision - transitioning to POST_TURN"

        decision_type = game.pending_decision.type
        if decision_type == "BUY":
            if cpu_player.cash >= game.pending_decision.price + 200:
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.BUY_PROPERTY, {}
                )
                updated_game = await self.orchestrator.get_game(game.id)
                if result.success:
                    return (
                        CpuTurnState(updated_game.turn_phase.value),
                        f"{cpu_player.name} bought property: {result.message}",
                    )
                else:
                    result = await self.orchestrator.perform_action(
                        game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
                    )
                    updated_game = await self.orchestrator.get_game(game.id)
                    return (
                        CpuTurnState(updated_game.turn_phase.value),
                        f"{cpu_player.name} passed (buy failed: {result.message})",
                    )
            else:
                result = await self.orchestrator.perform_action(
                    game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
                )
                updated_game = await self.orchestrator.get_game(game.id)
                return (
                    CpuTurnState(updated_game.turn_phase.value),
                    f"{cpu_player.name} passed on property (insufficient funds)",
                )
        elif decision_type in ("MARKET", "BLACK_MARKET"):
            result = await self.orchestrator.perform_action(
                game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
            )
            updated_game = await self.orchestrator.get_game(game.id)
            return (
                CpuTurnState(updated_game.turn_phase.value),
                f"{cpu_player.name} left Black Market",
            )
        else:
            result = await self.orchestrator.perform_action(
                game.id, cpu_player.id, ActionType.PASS_PROPERTY, {}
            )
            updated_game = await self.orchestrator.get_game(game.id)
            return (
                CpuTurnState(updated_game.turn_phase.value),
                f"{cpu_player.name} passed on decision type: {decision_type}",
            )

    async def _handle_cpu_post_turn(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, Optional[str]]:
        """Handle CPU post-turn phase."""
        turn_manager = self.orchestrator.turn_manager
        upgraded = await self.cpu_upgrade_properties(game, cpu_player, turn_manager)
        if upgraded:
            game = await self.orchestrator.get_game(game.id)
            cpu_player = next(
                (p for p in game.players if p.id == cpu_player.id), cpu_player
            )
            return CpuTurnState.POST_TURN, f"{cpu_player.name} upgraded a property"

        result = await self.orchestrator.perform_action(
            game.id, cpu_player.id, ActionType.END_TURN, {}
        )
        if result.success:
            return CpuTurnState.COMPLETE, f"{cpu_player.name} ended turn"
        else:
            return (
                CpuTurnState.COMPLETE,
                f"{cpu_player.name} failed to end turn: {result.message}",
            )

    async def _handle_cpu_moving(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, Optional[str]]:
        """Handle CPU moving phase - just wait for transition."""
        updated_game = await self.orchestrator.get_game(game.id)
        new_state = CpuTurnState(updated_game.turn_phase.value)
        return new_state, None

    async def _handle_cpu_auction(
        self, game: "GameSession", cpu_player: "Player"
    ) -> tuple[CpuTurnState, Optional[str]]:
        """Handle CPU auction phase."""
        return (
            CpuTurnState.AUCTION,
            f"{cpu_player.name} pausing turn for Auction",
        )

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

    async def simulate_cpu_game(self, game_id: str, max_turns: int = 100) -> dict:
        """Simulate a CPU-only game until completion or max turns."""
        game = await self.orchestrator.get_game(game_id)

        if game.status == GameStatus.LOBBY:
            if len(game.players) < 2:
                raise ValueError("Need at least 2 CPU players to simulate")
            game = await self.orchestrator.start_game(game_id, force=True)

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

        game = await self.orchestrator.get_game(game_id)
        return self._build_simulation_result(game, turns_played, turn_log)

    async def _handle_stuck_state(
        self, game: "GameSession", current_player: "Player", stuck_state: dict
    ) -> None:
        """Handle stuck state detection in simulation."""
        current_state = f"{game.turn_phase.value}:{current_player.id}:{game.pending_decision}"
        if current_state == stuck_state["last_state"]:
            stuck_state["counter"] += 1
            if stuck_state["counter"] > 5:
                game.turn_phase = TurnPhase.POST_TURN
                game.pending_decision = None
                await self.orchestrator.repository.update(game)
                stuck_state["counter"] = 0
        else:
            stuck_state["counter"] = 0
            stuck_state["last_state"] = current_state

    def _init_turn_info(
        self, game: "GameSession", current_player: "Player", turns_played: int
    ) -> dict:
        """Initialize turn info dict for simulation."""
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

    def _update_turn_info_post_turn(
        self, game: "GameSession", turn_info: dict
    ) -> None:
        """Update turn info after turn completes."""
        current_player = next(
            (p for p in game.players if p.id == turn_info["player_id"]), None
        )
        if current_player:
            turn_info["cash_after"] = current_player.cash
            turn_info["position_after"] = current_player.position

    def _check_simulation_end(self, game: "GameSession") -> bool:
        """Check if simulation should end."""
        active_players = [
            p for p in game.players if not p.is_bankrupt and p.cash >= 0
        ]
        if len(active_players) <= 1:
            game.status = GameStatus.FINISHED
            return True
        return False

    def _build_simulation_result(
        self, game: "GameSession", turns_played: int, turn_log: list
    ) -> dict:
        """Build simulation result dict."""
        return {
            "game_id": game.id,
            "status": game.status.value,
            "turns_played": turns_played,
            "rounds_played": game.current_round,
            "max_rounds": game.max_rounds,
            "winner": self.orchestrator.economy_manager.determine_winner(game),
            "final_standings": [
                {
                    "name": p.name,
                    "cash": p.cash,
                    "properties": len(p.properties),
                    "bankrupt": p.is_bankrupt,
                }
                for p in sorted(game.players, key=lambda x: x.cash, reverse=True)
            ],
            "turn_log": turn_log[-10:],
        }

    async def _execute_simulated_turn(
        self, game_id: str, current_player: "Player", turn_info: dict
    ) -> bool:
        """Execute a single turn in the simulation. Returns True if game over."""
        game = await self.orchestrator.get_game(game_id)

        if game.turn_phase == TurnPhase.PRE_ROLL:
            result = await self.orchestrator.perform_action(
                game_id, current_player.id, ActionType.ROLL_DICE, {}
            )
            turn_info["actions"].append({"action": "ROLL_DICE", "result": result.message})
            game = await self.orchestrator.get_game(game_id)

        if game.turn_phase == TurnPhase.DECISION and game.pending_decision:
            await self._handle_simulated_decision(game_id, current_player, turn_info)
            game = await self.orchestrator.get_game(game_id)

        await self._simulate_cpu_trades(game, turn_info)
        game = await self.orchestrator.get_game(game_id)

        if game.turn_phase == TurnPhase.POST_TURN:
            result = await self.orchestrator.perform_action(
                game_id, current_player.id, ActionType.END_TURN, {}
            )
            turn_info["actions"].append({"action": "END_TURN", "result": result.message})
            game = await self.orchestrator.get_game(game_id)

            if result.data and result.data.get("game_over"):
                turn_info["actions"].append(
                    {"action": "GAME_OVER", "result": result.message}
                )
                return True

        return False

    async def _handle_simulated_decision(
        self, game_id: str, current_player: "Player", turn_info: dict
    ) -> None:
        """Handle decision phase in simulation."""
        game = await self.orchestrator.get_game(game_id)
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
                result = await self.orchestrator.perform_action(
                    game_id, game_current_player.id, ActionType.BUY_PROPERTY, {}
                )
                turn_info["actions"].append(
                    {"action": "BUY_PROPERTY", "result": result.message}
                )
            else:
                result = await self.orchestrator.perform_action(
                    game_id, game_current_player.id, ActionType.PASS_PROPERTY, {}
                )
                turn_info["actions"].append(
                    {"action": "PASS_PROPERTY", "result": result.message}
                )

        elif decision_type == "MARKET":
            buffs = (
                game.pending_decision.event_data.get("buffs", [])
                if game.pending_decision.event_data
                else []
            )
            bought = False

            if game_current_player and not game_current_player.active_buff:
                for buff in buffs:
                    if (
                        game_current_player
                        and game_current_player.cash >= buff["cost"] + 300
                    ):
                        result = await self.orchestrator.perform_action(
                            game_id,
                            game_current_player.id,
                            ActionType.BUY_BUFF,
                            {"buff_id": buff["id"]},
                        )
                        turn_info["actions"].append(
                            {"action": "BUY_BUFF", "result": result.message}
                        )
                        bought = True
                        break

            if not bought:
                result = await self.orchestrator.perform_action(
                    game_id, current_player.id, ActionType.PASS_PROPERTY, {}
                )
                turn_info["actions"].append(
                    {"action": "PASS_MARKET", "result": result.message}
                )

        else:
            turn_info["actions"].append(
                {
                    "action": f"SKIP_{decision_type}",
                    "result": f"Skipped unknown decision: {decision_type}",
                }
            )
            game.pending_decision = None
            game.turn_phase = TurnPhase.POST_TURN
            await self.orchestrator.repository.update(game)

    async def _simulate_cpu_trades(
        self, game: "GameSession", turn_info: dict
    ) -> None:
        """Handle CPU trading logic in simulation."""
        await self._process_incoming_trade_offers(game, turn_info)

        current_player = next(
            (p for p in game.players if p.id == game.current_turn_player_id), None
        )
        if game.turn_phase == TurnPhase.POST_TURN and current_player:
            await self._attempt_cpu_trade_proposal(game, current_player, turn_info)

    async def _process_incoming_trade_offers(
        self, game: "GameSession", turn_info: dict
    ) -> None:
        """Process trade offers sent to CPU players."""
        for offer in list(game.active_trade_offers):
            target = next((p for p in game.players if p.id == offer.target_id), None)
            if target:
                if random.random() < 0.3:
                    res = await self.orchestrator.perform_action(
                        game.id,
                        target.id,
                        ActionType.ACCEPT_TRADE,
                        {"trade_id": offer.id},
                    )
                    turn_info["actions"].append(
                        {
                            "action": f"ACCEPT_TRADE ({target.name})",
                            "result": res.message,
                        }
                    )
                else:
                    res = await self.orchestrator.perform_action(
                        game.id,
                        target.id,
                        ActionType.DECLINE_TRADE,
                        {"trade_id": offer.id},
                    )
                    turn_info["actions"].append(
                        {
                            "action": f"DECLINE_TRADE ({target.name})",
                            "result": res.message,
                        }
                    )

    async def _attempt_cpu_trade_proposal(
        self, game: "GameSession", current_player: "Player", turn_info: dict
    ) -> None:
        """Attempt to propose a trade from the current CPU player."""
        if random.random() >= 0.1:
            return

        potential_targets = [p for p in game.players if p.id != current_player.id]
        if not potential_targets:
            return

        target = random.choice(potential_targets)

        my_props = [t.id for t in game.board if t.owner_id == current_player.id]
        their_props = [t.id for t in game.board if t.owner_id == target.id]

        offer_props = (
            [random.choice(my_props)] if my_props and random.random() < 0.5 else []
        )
        req_props = (
            [random.choice(their_props)]
            if their_props and random.random() < 0.5
            else []
        )

        offer_cash = min(current_player.cash, 100) if random.random() < 0.5 else 0

        if not offer_props and not req_props and offer_cash == 0:
            return

        payload = {
            "target_id": target.id,
            "offer_cash": offer_cash,
            "req_cash": 0,
            "offer_props": offer_props,
            "req_props": req_props,
        }

        res = await self.orchestrator.perform_action(
            game.id, current_player.id, ActionType.PROPOSE_TRADE, payload
        )
        turn_info["actions"].append({"action": "PROPOSE_TRADE", "result": res.message})

    async def _check_bankruptcy(self, game_id: str) -> "GameSession":
        """Check for bankrupt players and mark them."""
        game = await self.orchestrator.get_game(game_id)

        for player in game.players:
            if player.cash < 0:
                player.cash = -9999
                await self.orchestrator.repository.update_player_cash(
                    player.id, player.cash
                )

        return await self.orchestrator.get_game(game_id)
