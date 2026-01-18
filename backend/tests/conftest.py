"""Pytest configuration and fixtures."""
import pytest
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.db.session import _get_db_manager


@pytest.fixture
async def db_database():
    """MongoDB database for isolated tests."""
    # Use test database - connect to localhost
    test_db_name = f"test_sastaspace_{os.getpid()}"
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    
    client = AsyncIOMotorClient(mongodb_url)
    database = client[test_db_name]
    
    # Clear collections before each test
    await database.game_sessions.delete_many({})
    await database.players.delete_many({})
    await database.tiles.delete_many({})
    await database.submitted_tiles.delete_many({})
    
    yield database
    
    # Cleanup - drop the test database
    await database.client.drop_database(test_db_name)
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
