"""Pytest configuration and fixtures."""
import pytest
import duckdb
from app.modules.sastadice.models import init_tables


@pytest.fixture
def db_cursor():
    """In-memory DuckDB for isolated tests."""
    conn = duckdb.connect(":memory:")
    cursor = conn.cursor()
    init_tables(cursor)
    yield cursor
    cursor.close()
    conn.close()


@pytest.fixture
def sample_tile_create():
    """Sample tile creation schema for tests."""
    from app.modules.sastadice.schemas import TileCreate, TileType

    return TileCreate(type=TileType.PROPERTY, name="Test Property", effect_config={})


@pytest.fixture
def sample_player_create():
    """Sample player creation schema for tests."""
    from app.modules.sastadice.schemas import PlayerCreate

    return PlayerCreate(name="Test Player")
