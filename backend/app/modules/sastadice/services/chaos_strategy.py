"""Chaos testing strategy with fault injection for resilience testing."""
import random
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import ChaosConfig, Player, GameSession
    from app.modules.sastadice.repository import GameRepository

logger = logging.getLogger(__name__)


class SimulatedDBWriteError(Exception):
    """Simulated database write failure for testing."""
    pass


class SimulatedNetworkError(Exception):
    """Simulated network partition for testing."""
    pass


class MonkeyStrategy:
    """CPU strategy that makes intentionally suboptimal/random decisions for chaos testing."""
    
    def __init__(self, config: "ChaosConfig"):
        self.rng = random.Random(config.seed)
        self.chaos_prob = config.chaos_probability
        self.faults = config.fault_injection
        logger.info(f"MonkeyStrategy initialized with seed: {config.seed}, chaos_prob: {config.chaos_probability}")
    
    def should_make_stupid_move(self) -> bool:
        """Decide if CPU should make a suboptimal move."""
        return self.rng.random() < self.chaos_prob
    
    def get_auction_bid(self, player: "Player", property_price: int) -> int:
        """
        Determine auction bid amount.
        
        Chaos behavior: 30% chance to bid entire cash (greedy/stupid).
        Normal: Bid up to 80% of property price.
        """
        if self.should_make_stupid_move():
            logger.debug(f"MonkeyStrategy: {player.name} bidding all cash ${player.cash}")
            return player.cash
        return min(player.cash, int(property_price * 0.8))
    
    def should_buy_property(self, player: "Player", price: int, buffer: int = 200) -> bool:
        """
        Decide whether to buy a property.
        
        Chaos behavior: 20% chance to pass even with excess cash.
        Normal: Buy if cash >= price + buffer.
        """
        if self.should_make_stupid_move():
            logger.debug(f"MonkeyStrategy: {player.name} passing on property (chaos)")
            return False
        return player.cash >= price + buffer
    
    def should_propose_invalid_trade(self) -> bool:
        """
        Chaos behavior: 10% chance to propose invalid/unfulfillable trade.
        Purpose: Test validation logic.
        """
        return self.should_make_stupid_move() and self.rng.random() < 0.1
    
    def should_buy_buff_randomly(self, player: "Player", buff_cost: int) -> bool:
        """
        Decide whether to buy a buff.
        
        Chaos behavior: 15% chance to randomly select regardless of cost.
        Normal: Only buy if affordable with buffer.
        """
        if self.should_make_stupid_move() and self.rng.random() < 0.15:
            logger.debug(f"MonkeyStrategy: {player.name} trying to buy buff despite cost")
            return True
        return player.cash >= buff_cost + 300
    
    def should_skip_upgrade(self) -> bool:
        """
        Chaos behavior: 25% chance to skip optimal upgrade.
        Purpose: Test color set logic and game progression.
        """
        return self.should_make_stupid_move() and self.rng.random() < 0.25
    
    async def maybe_inject_fault(self, action: str) -> None:
        """
        Inject infrastructure faults based on config.
        
        Raises:
            SimulatedDBWriteError: If DB write failure simulated
            SimulatedNetworkError: If network partition simulated
        """
        if self.faults.delay_responses_ms > 0:
            await asyncio.sleep(self.faults.delay_responses_ms / 1000)
        
        if self.rng.random() < self.faults.drop_db_writes:
            logger.warning(f"CHAOS: Simulated DB write failure on {action}")
            raise SimulatedDBWriteError(f"Injected DB failure on {action}")
        
        if self.faults.network_partition:
            logger.warning(f"CHAOS: Simulated network partition on {action}")
            raise SimulatedNetworkError("Injected network partition")


class ChaosRepository:
    """Wrapper around GameRepository that injects faults for resilience testing."""
    
    def __init__(self, real_repo: "GameRepository", config: "ChaosConfig"):
        self._repo = real_repo
        self._config = config
        self._rng = random.Random(config.seed + 1)  # Different seed for repo
        logger.info(f"ChaosRepository initialized with drop_db_writes={config.fault_injection.drop_db_writes}")
    
    async def update(self, game: "GameSession") -> None:
        """Update game with optional fault injection."""
        if self._rng.random() < self._config.fault_injection.drop_db_writes:
            logger.warning(f"CHAOS: Dropped DB write for game {game.id}")
            return
        await self._repo.update(game)
    
    async def update_player_cash(self, player_id: str, cash: int) -> None:
        """Update player cash with optional fault injection."""
        if self._rng.random() < self._config.fault_injection.drop_db_writes:
            logger.warning(f"CHAOS: Dropped cash update for player {player_id}")
            return
        await self._repo.update_player_cash(player_id, cash)
    
    async def update_tile_owner(self, tile_id: str, owner_id: str | None) -> None:
        """Update tile owner with optional fault injection."""
        if self._rng.random() < self._config.fault_injection.drop_db_writes:
            logger.warning(f"CHAOS: Dropped ownership update for tile {tile_id}")
            return
        await self._repo.update_tile_owner(tile_id, owner_id)
    
    async def save_board(self, game_id: str, board: list) -> None:
        """Save board with optional fault injection."""
        if self._rng.random() < self._config.fault_injection.drop_db_writes:
            logger.warning(f"CHAOS: Dropped board save for game {game_id}")
            return
        await self._repo.save_board(game_id, board)
    
    def __getattr__(self, name):
        return getattr(self._repo, name)
