"""Pytest configuration and fixtures."""

import pytest
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture
async def db_database():
    """In-memory MongoDB mock for fast isolated tests."""
    client = AsyncMongoMockClient()
    database = client["test_sastaspace"]

    yield database

    client.close()


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
