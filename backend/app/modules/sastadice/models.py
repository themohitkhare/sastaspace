"""DuckDB table definitions and initialization for SastaDice."""
import duckdb


def init_tables(cursor: duckdb.DuckDBCursor) -> None:
    """Initialize all SastaDice tables in DuckDB."""
    # Game sessions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_game_sessions (
            id VARCHAR PRIMARY KEY,
            status VARCHAR NOT NULL DEFAULT 'LOBBY',
            current_turn_player_id VARCHAR,
            board_size INTEGER DEFAULT 0,
            version INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Players table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_players (
            id VARCHAR PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            cash INTEGER DEFAULT 1500,
            position INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES sd_game_sessions(id)
        )
        """
    )

    # Tiles table (final board tiles)
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
