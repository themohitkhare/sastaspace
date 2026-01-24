"""Simulation manager for CPU-only game testing."""
import random
from dataclasses import asdict
from typing import TYPE_CHECKING

from app.modules.sastadice.schemas import ActionType, GameSession, GameStatus, Player, TileType
from app.modules.sastadice.services.inflation_monitor import EconomicViolationError, InflationMonitor
from app.modules.sastadice.services.invariant_checker import InvariantChecker, InvariantViolationError, StrictnessMode
from app.modules.sastadice.services.snapshot_manager import SnapshotManager

if TYPE_CHECKING:
    from app.modules.sastadice.repository import GameRepository
    from app.modules.sastadice.services.action_dispatcher import ActionDispatcher


class SimulationManager:
    """Handles CPU game simulation for testing."""

    def __init__(
        self,
        repository: "GameRepository",
        action_dispatcher: "ActionDispatcher",
        get_game_callback,
        start_game_callback,
        strictness_mode: StrictnessMode = StrictnessMode.STRICT,
        enable_economic_monitoring: bool = False,
    ) -> None:
        self.repository = repository
        self.action_dispatcher = action_dispatcher
        self._get_game = get_game_callback
        self._start_game = start_game_callback
        self.invariant_checker = InvariantChecker(mode=strictness_mode)
        self.snapshot_manager = SnapshotManager()
        self.inflation_monitor = InflationMonitor() if enable_economic_monitoring else None
        self.enable_economic_monitoring = enable_economic_monitoring

    async def simulate_cpu_game(self, game_id: str, max_turns: int = 100) -> dict:
        """Simulate a CPU-only game until completion or max turns."""
        game = await self._get_game(game_id)

        if game.status == GameStatus.LOBBY:
            if len(game.players) < 2:
                raise ValueError("Need at least 2 CPU players to simulate")
            game = await self._start_game(game_id, force=True)

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
            
            # Check invariants after turn
            game = await self._get_game(game_id)
            violations = self.invariant_checker.check_all(game)
            if violations:
                critical = [v for v in violations if v.severity == "CRITICAL"]
                if critical:
                    turn_info["invariant_violations"] = [asdict(v) for v in critical]
                    turn_log.append(turn_info)
                    snapshot_path = self.snapshot_manager.capture(
                        game,
                        reason="invariant_violation",
                        error=f"Invariant violations: {len(critical)}",
                        violations=critical,
                    )
                    
                    raise InvariantViolationError(
                        f"Invariant violations: {len(critical)}. Snapshot: {snapshot_path}"
                    )
            
            # Check economic health (if enabled)
            if self.enable_economic_monitoring and self.inflation_monitor:
                # Track when we move to a new round (first player)
                if game.current_turn_player_id == game.first_player_id:
                    self.inflation_monitor.record_round_end(game)
                    economic_violations = self.inflation_monitor.check_economic_health(game)
                    
                    if economic_violations:
                        turn_info["economic_violations"] = economic_violations
                        turn_log.append(turn_info)
                        
                        # Generate economic report
                        report = self.inflation_monitor.generate_report(game)
                        
                        # Capture snapshot
                        snapshot_path = self.snapshot_manager.capture(
                            game,
                            reason="economic_violation",
                            error=f"Economic violations: {len(economic_violations)}",
                            violations=economic_violations
                        )
                        
                        raise EconomicViolationError(
                            f"Economic violations detected: {economic_violations}\n"
                            f"Diagnosis: {report.diagnosis}\n"
                            f"Snapshot saved to: {snapshot_path}"
                        )
            
            turn_log.append(turn_info)
            turns_played += 1

            game = await self._check_bankruptcy(game_id)
            if self._check_simulation_end(game):
                break

        game = await self._get_game(game_id)
        
        # Generate final economic report if monitoring enabled
        if self.enable_economic_monitoring and self.inflation_monitor:
            final_report = self.inflation_monitor.generate_report(game)
            return {
                **self._build_simulation_result(game, turns_played, turn_log),
                "economic_report": {
                    "diagnosis": final_report.diagnosis,
                    "inflation_detected": final_report.inflation_detected,
                    "stalemate_detected": final_report.stalemate_detected,
                    "recommendations": final_report.recommendations
                }
            }
        
        return self._build_simulation_result(game, turns_played, turn_log)

    async def _handle_stuck_state(
        self, game: GameSession, current_player: Player, stuck_state: dict
    ) -> None:
        from app.modules.sastadice.schemas import TurnPhase

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

    def _init_turn_info(
        self, game: GameSession, current_player: Player, turns_played: int
    ) -> dict:
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

    def _build_simulation_result(
        self, game: GameSession, turns_played: int, turn_log: list
    ) -> dict:
        from app.modules.sastadice.services.economy_manager import EconomyManager

        economy_manager = EconomyManager(self.repository)
        winner = economy_manager.determine_winner(game)

        return {
            "game_id": game.id,
            "status": game.status.value,
            "turns_played": turns_played,
            "rounds_played": game.current_round,
            "max_rounds": game.max_rounds,
            "winner": winner,
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
        self, game_id: str, current_player: Player, turn_info: dict
    ) -> bool:
        """Execute a single turn in the simulation. Returns True if game over."""
        game = await self._get_game(game_id)

        if game.turn_phase.value == "PRE_ROLL":
            result = await self.action_dispatcher.dispatch(
                game, current_player.id, ActionType.ROLL_DICE, {}
            )
            turn_info["actions"].append({"action": "ROLL_DICE", "result": result.message})
            game = await self._get_game(game_id)

        if game.turn_phase.value == "DECISION" and game.pending_decision:
            await self._handle_simulated_decision(game_id, current_player, turn_info)
            game = await self._get_game(game_id)

        await self._simulate_cpu_trades(game, turn_info)
        game = await self._get_game(game_id)

        if game.turn_phase.value == "POST_TURN":
            result = await self.action_dispatcher.dispatch(
                game, current_player.id, ActionType.END_TURN, {}
            )
            turn_info["actions"].append({"action": "END_TURN", "result": result.message})
            game = await self._get_game(game_id)

            if result.data and result.data.get("game_over"):
                turn_info["actions"].append(
                    {"action": "GAME_OVER", "result": result.message}
                )
                return True

        return False

    async def _handle_simulated_decision(
        self, game_id: str, current_player: Player, turn_info: dict
    ) -> None:
        game = await self._get_game(game_id)

        tile = game.board[current_player.position] if current_player.position < len(game.board) else None
        if tile and tile.type == TileType.NODE and not tile.owner_id:
            if current_player.cash >= tile.price + 200:
                result = await self.action_dispatcher.dispatch(
                    game, current_player.id, ActionType.BUY_PROPERTY, {}
                )
                turn_info["actions"].append({"action": "BUY_NODE", "result": result.message})
                return

        if tile and tile.type == TileType.GO_TO_JAIL:
            turn_info["actions"].append({"action": "SENT_TO_JAIL", "result": "Landed on 404"})
            return

        if current_player.in_jail:
            bribe_cost = game.settings.jail_bribe_cost
            if current_player.cash >= bribe_cost + 300:
                result = await self.action_dispatcher.dispatch(
                    game, current_player.id, ActionType.BUY_RELEASE, {}
                )
            else:
                result = await self.action_dispatcher.dispatch(
                    game, current_player.id, ActionType.ROLL_FOR_DOUBLES, {}
                )
            turn_info["actions"].append({"action": "JAIL_ESCAPE", "result": result.message})
            return

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
                result = await self.action_dispatcher.dispatch(
                    game, game_current_player.id, ActionType.BUY_PROPERTY, {}
                )
                turn_info["actions"].append(
                    {"action": "BUY_PROPERTY", "result": result.message}
                )
            else:
                result = await self.action_dispatcher.dispatch(
                    game, game_current_player.id, ActionType.PASS_PROPERTY, {}
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
                        result = await self.action_dispatcher.dispatch(
                            game,
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
                result = await self.action_dispatcher.dispatch(
                    game, current_player.id, ActionType.PASS_PROPERTY, {}
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
            from app.modules.sastadice.schemas import TurnPhase
            game.turn_phase = TurnPhase.POST_TURN
            await self.repository.update(game)

    async def _simulate_cpu_trades(self, game: GameSession, turn_info: dict) -> None:
        await self._process_incoming_trade_offers(game, turn_info)

        current_player = next(
            (p for p in game.players if p.id == game.current_turn_player_id), None
        )
        if game.turn_phase.value == "POST_TURN" and current_player:
            await self._attempt_cpu_trade_proposal(game, current_player, turn_info)

    async def _process_incoming_trade_offers(
        self, game: GameSession, turn_info: dict
    ) -> None:
        for offer in list(game.active_trade_offers):
            target = next((p for p in game.players if p.id == offer.target_id), None)
            if target:
                if random.random() < 0.3:
                    res = await self.action_dispatcher.dispatch(
                        game, target.id, ActionType.ACCEPT_TRADE, {"trade_id": offer.id}
                    )
                    turn_info["actions"].append(
                        {
                            "action": f"ACCEPT_TRADE ({target.name})",
                            "result": res.message,
                        }
                    )
                else:
                    res = await self.action_dispatcher.dispatch(
                        game, target.id, ActionType.DECLINE_TRADE, {"trade_id": offer.id}
                    )
                    turn_info["actions"].append(
                        {
                            "action": f"DECLINE_TRADE ({target.name})",
                            "result": res.message,
                        }
                    )

    async def _attempt_cpu_trade_proposal(
        self, game: GameSession, current_player: Player, turn_info: dict
    ) -> None:
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
            [random.choice(their_props)] if their_props and random.random() < 0.5 else []
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

        res = await self.action_dispatcher.dispatch(
            game, current_player.id, ActionType.PROPOSE_TRADE, payload
        )
        turn_info["actions"].append({"action": "PROPOSE_TRADE", "result": res.message})

    async def _check_bankruptcy(self, game_id: str) -> GameSession:
        game = await self._get_game(game_id)

        for player in game.players:
            if player.cash < 0:
                player.cash = -9999
                await self.repository.update_player_cash(player.id, player.cash)

        return await self._get_game(game_id)
