"""Jail manager for jail entry, exit, and 3-turn maximum enforcement."""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player, Tile


class JailManager:
    """Handles jail entry, exit, and 3-turn maximum enforcement."""

    MAX_JAIL_TURNS = 3

    @staticmethod
    def send_to_jail(game: "GameSession", player: "Player") -> None:
        """Send player to Server Downtime position."""
        jail_pos = len(game.board) // 2
        player.position = jail_pos
        player.in_jail = True
        player.jail_turns = 0
        player.consecutive_doubles = 0

    @staticmethod
    def attempt_bribe_release(
        game: "GameSession", player: "Player"
    ) -> tuple[bool, str]:
        """Pay bribe to exit jail. Returns (success, message)."""
        bribe_cost = game.settings.jail_bribe_cost

        if not player.in_jail:
            return False, "You are not in jail"

        if player.cash < bribe_cost:
            return False, f"Not enough cash. Need ${bribe_cost}"

        player.cash -= bribe_cost
        player.in_jail = False
        player.jail_turns = 0
        return True, f"Paid ${bribe_cost} bribe. You are free!"

    @staticmethod
    def roll_for_doubles(
        game: "GameSession", player: "Player"
    ) -> tuple[bool, int, int, str]:
        """
        Roll dice to escape jail.
        Returns (escaped, dice1, dice2, message).

        If 3rd failed attempt, forces bribe payment or auto-release.
        """
        if not player.in_jail:
            return False, 0, 0, "You are not in jail"

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        is_doubles = dice1 == dice2

        player.jail_turns += 1

        if is_doubles:
            player.in_jail = False
            player.jail_turns = 0
            return True, dice1, dice2, f"Rolled doubles ({dice1}, {dice2})! You escaped!"

        if player.jail_turns >= JailManager.MAX_JAIL_TURNS:
            bribe_cost = game.settings.jail_bribe_cost
            if player.cash >= bribe_cost:
                player.cash -= bribe_cost
                msg = f"3rd turn! Forced to pay ${bribe_cost}. You are free."
            else:
                msg = "3rd turn! Auto-released (no cash for bribe)."
            player.in_jail = False
            player.jail_turns = 0
            return True, dice1, dice2, msg

        turns_left = JailManager.MAX_JAIL_TURNS - player.jail_turns
        return (
            False,
            dice1,
            dice2,
            f"No doubles ({dice1}, {dice2}). {turns_left} attempts left.",
        )

    @staticmethod
    def can_collect_rent(
        player: "Player", tile: "Tile", game: "GameSession"  # type: ignore
    ) -> bool:
        """
        Players in jail CAN still collect rent (unless DDoS/blocked).
        This returns True unless tile is blocked.
        """
        if tile.blocked_until_round and tile.blocked_until_round > game.current_round:
            return False
        if tile.id in game.blocked_tiles:
            return False
        return True
