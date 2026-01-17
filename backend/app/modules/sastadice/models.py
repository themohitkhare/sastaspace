"""DuckDB table definitions and initialization for SastaDice."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb


def init_tables(cursor) -> None:  # type: ignore
    """Initialize all SastaDice tables in DuckDB."""
    # Game sessions table with turn phase state machine
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_game_sessions (
            id VARCHAR PRIMARY KEY,
            status VARCHAR NOT NULL DEFAULT 'LOBBY',
            turn_phase VARCHAR NOT NULL DEFAULT 'PRE_ROLL',
            current_turn_player_id VARCHAR,
            host_id VARCHAR,
            board_size INTEGER DEFAULT 0,
            version INTEGER DEFAULT 0,
            starting_cash INTEGER DEFAULT 0,
            go_bonus INTEGER DEFAULT 0,
            last_dice_roll JSON,
            pending_decision JSON,
            last_event_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_players (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            cash INTEGER DEFAULT 0,
            position INTEGER DEFAULT 0,
            color VARCHAR DEFAULT '#888888',
            properties JSON DEFAULT '[]',
            ready BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES sd_game_sessions(id)
        )
        """
    )

    # Tiles table (final board tiles) with price and rent
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_tiles (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            owner_id VARCHAR,
            type VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            effect_config JSON,
            position INTEGER NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            price INTEGER DEFAULT 0,
            rent INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES sd_game_sessions(id)
        )
        """
    )

    # Submitted tiles table (player submissions before board generation)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_submitted_tiles (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            effect_config JSON,
            FOREIGN KEY (game_id) REFERENCES sd_game_sessions(id),
            FOREIGN KEY (player_id) REFERENCES sd_players(id)
        )
        """
    )
