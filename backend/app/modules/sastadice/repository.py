"""Game repository for MongoDB operations."""

import uuid
from datetime import UTC, datetime

from app.core.db_repo import BaseRepository
from app.modules.sastadice.models import (
    GameSessionDocument,
    PlayerDocument,
    SubmittedTileDocument,
    TileDocument,
)
from app.modules.sastadice.schemas import (
    PLAYER_COLORS,
    GameSession,
    GameStatus,
    Player,
    PlayerCreate,
    Tile,
    TileCreate,
    TileType,
    TurnPhase,
)


class GameRepository(BaseRepository[GameSession]):
    """Repository for game session operations."""

    async def get_by_id(self, id: str) -> GameSession | None:
        """Get game session by ID or short code (first 8 chars)."""
        if len(id) < 32:
            short_id = id.lower()
            game_doc = await self.database.game_sessions.find_one(
                {"_id": {"$regex": f"^{short_id}", "$options": "i"}}
            )
        else:
            game_doc = await self.database.game_sessions.find_one({"_id": id})
            if not game_doc:
                game_doc = await self.database.game_sessions.find_one({"_id": id.lower()})

        if not game_doc:
            return None

        game_document = GameSessionDocument.model_validate(game_doc)
        players = await self._get_players(game_document.id)
        board = await self._get_board_tiles(game_document.id)

        return game_document.to_game_session(players, board)

    async def create(self, entity: GameSession) -> GameSession:
        """Create a new game session."""
        game_id = entity.id if entity.id else str(uuid.uuid4())
        entity.id = game_id

        game_doc = GameSessionDocument.from_game_session(entity)
        await self.database.game_sessions.insert_one(game_doc.to_dict())

        return entity

    async def create_game(self) -> GameSession:
        """Create a new empty game session."""
        game = GameSession(
            id=str(uuid.uuid4()),
            status=GameStatus.LOBBY,
            turn_phase=TurnPhase.PRE_ROLL,
            board_size=0,
        )
        return await self.create(game)

    async def update(self, entity: GameSession) -> GameSession:
        """Update game session."""
        game_doc = GameSessionDocument.from_game_session(entity)
        update_data = game_doc.to_dict()

        # to_dict uses exclude_none=True, so explicitly unset None fields
        if entity.auction_state is None:
            update_data["auction_state"] = None
        if entity.pending_decision is None:
            update_data["pending_decision"] = None

        update_data.pop("_id", None)
        update_data.pop("version", None)

        await self.database.game_sessions.update_one(
            {"_id": entity.id}, {"$set": update_data, "$inc": {"version": 1}}
        )
        return entity

    async def delete(self, id: str) -> bool:
        """Delete game session by ID."""
        result = await self.database.game_sessions.delete_one({"_id": id})
        return result.deleted_count > 0

    async def get_version(self, game_id: str) -> int:
        """Get current version number for polling optimization."""
        game_doc = await self.database.game_sessions.find_one({"_id": game_id}, {"version": 1})
        return game_doc.get("version", 0) if game_doc else 0

    async def add_player(self, game_id: str, player_create: PlayerCreate) -> Player:
        """Add a player to a game."""
        player_id = str(uuid.uuid4())

        count = await self.database.players.count_documents({"game_id": game_id})
        color = PLAYER_COLORS[count % len(PLAYER_COLORS)]

        player_doc = PlayerDocument(
            id=player_id,
            game_id=game_id,
            name=player_create.name,
            cash=0,
            position=0,
            color=color,
            properties=[],
            ready=False,
            is_bankrupt=False,
            created_at=datetime.now(UTC),
        )

        await self.database.players.insert_one(player_doc.to_dict())

        submitted_tiles = await self._get_submitted_tiles(game_id, player_id)

        return Player(
            id=player_id,
            name=player_create.name,
            cash=0,
            position=0,
            color=color,
            properties=[],
            submitted_tiles=submitted_tiles,
            ready=False,
        )

    async def toggle_player_ready(self, player_id: str) -> bool:
        """Toggle player's ready status. Returns new ready state."""
        player_doc = await self.database.players.find_one({"_id": player_id})
        if not player_doc:
            return False

        new_ready = not player_doc.get("ready", False)
        await self.database.players.update_one({"_id": player_id}, {"$set": {"ready": new_ready}})
        return new_ready

    async def are_all_players_ready(self, game_id: str) -> bool:
        """Check if all players in a game are ready."""
        total = await self.database.players.count_documents({"game_id": game_id})
        if total == 0:
            return False

        ready_count = await self.database.players.count_documents(
            {"game_id": game_id, "ready": True}
        )
        return total == ready_count

    async def set_host(self, game_id: str, player_id: str) -> None:
        """Set the host of a game."""
        await self.database.game_sessions.update_one(
            {"_id": game_id}, {"$set": {"host_id": player_id}, "$inc": {"version": 1}}
        )

    async def remove_player(self, game_id: str, player_id: str) -> bool:
        """Remove a player from a game. Returns True if player was removed."""
        await self.database.submitted_tiles.delete_many(
            {"game_id": game_id, "player_id": player_id}
        )

        result = await self.database.players.delete_one({"_id": player_id, "game_id": game_id})

        await self.database.game_sessions.update_one({"_id": game_id}, {"$inc": {"version": 1}})

        return result.deleted_count > 0

    async def submit_tiles(self, game_id: str, player_id: str, tiles: list[TileCreate]) -> None:
        """Submit tiles for a player."""
        await self.database.submitted_tiles.delete_many(
            {"game_id": game_id, "player_id": player_id}
        )

        for tile in tiles:
            tile_id = str(uuid.uuid4())
            tile_doc = SubmittedTileDocument.from_tile_create(tile, game_id, player_id, tile_id)
            await self.database.submitted_tiles.insert_one(tile_doc.to_dict())

    async def save_board(self, game_id: str, tiles: list[Tile]) -> None:
        """Save board tiles to database."""
        await self.database.tiles.delete_many({"game_id": game_id})

        for tile in tiles:
            tile_doc = TileDocument.from_tile(tile, game_id)
            await self.database.tiles.insert_one(tile_doc.to_dict())

    async def update_game_status(self, game_id: str, status: GameStatus) -> GameSession | None:
        """Update game status."""
        await self.database.game_sessions.update_one(
            {"_id": game_id}, {"$set": {"status": status.value}, "$inc": {"version": 1}}
        )
        game = await self.get_by_id(game_id)
        if game:
            game.status = status
        return game

    async def update_player_position(self, player_id: str, position: int) -> None:
        """Update player's board position."""
        await self.database.players.update_one({"_id": player_id}, {"$set": {"position": position}})

    async def update_player_cash(self, player_id: str, cash: int) -> None:
        """Update player's cash."""
        await self.database.players.update_one({"_id": player_id}, {"$set": {"cash": cash}})

    async def update_player_properties(self, player_id: str, properties: list[str]) -> None:
        """Update player's owned properties."""
        await self.database.players.update_one(
            {"_id": player_id}, {"$set": {"properties": properties}}
        )

    async def update_tile_owner(self, tile_id: str, owner_id: str) -> None:
        """Update tile ownership."""
        await self.database.tiles.update_one({"_id": tile_id}, {"$set": {"owner_id": owner_id}})

    async def set_players_starting_cash(self, game_id: str, starting_cash: int) -> None:
        """Set starting cash for all players in a game."""
        await self.database.players.update_many(
            {"game_id": game_id}, {"$set": {"cash": starting_cash}}
        )

    async def update_player_bankrupt(self, player_id: str, is_bankrupt: bool) -> None:
        """Update player's bankruptcy status."""
        await self.database.players.update_one(
            {"_id": player_id}, {"$set": {"is_bankrupt": is_bankrupt}}
        )

    async def update_player_buff(self, player_id: str, buff: str | None) -> None:
        """Update player's active buff."""
        await self.database.players.update_one({"_id": player_id}, {"$set": {"active_buff": buff}})

    async def update_player_skip_next_move(self, player_id: str, skip: bool) -> None:
        """Update player's skip_next_move flag."""
        await self.database.players.update_one(
            {"_id": player_id}, {"$set": {"skip_next_move": skip}}
        )

    async def update_player_double_rent_next_turn(self, player_id: str, double: bool) -> None:
        """Update player's double_rent_next_turn flag."""
        await self.database.players.update_one(
            {"_id": player_id}, {"$set": {"double_rent_next_turn": double}}
        )

    async def update_player_afk(
        self,
        player_id: str,
        afk_turns: int,
        disconnected: bool,
        disconnected_turns: int | None = None,
    ) -> None:
        """Update player's AFK/disconnection status."""
        update = {"afk_turns": afk_turns, "disconnected": disconnected}
        if disconnected_turns is not None:
            update["disconnected_turns"] = disconnected_turns
        await self.database.players.update_one(
            {"_id": player_id},
            {"$set": update},
        )

    async def update_player_jail(self, player_id: str, in_jail: bool, jail_turns: int = 0) -> None:
        """Update player's jail status."""
        await self.database.players.update_one(
            {"_id": player_id}, {"$set": {"in_jail": in_jail, "jail_turns": jail_turns}}
        )

    async def _get_players(self, game_id: str) -> list[Player]:
        """Get all players for a game ordered by join time."""
        cursor = self.database.players.find({"game_id": game_id}).sort("created_at", 1)
        players = []

        async for player_doc in cursor:
            player_document = PlayerDocument.model_validate(player_doc)
            submitted_tiles = await self._get_submitted_tiles(game_id, player_document.id)
            players.append(player_document.to_player(submitted_tiles))

        return players

    async def _get_submitted_tiles(self, game_id: str, player_id: str) -> list[TileCreate]:
        """Get submitted tiles for a player."""
        cursor = self.database.submitted_tiles.find({"game_id": game_id, "player_id": player_id})

        tiles = []
        async for tile_doc in cursor:
            tile_doc["type"] = TileType(tile_doc["type"])
            tile_document = SubmittedTileDocument.model_validate(tile_doc)
            tiles.append(tile_document.to_tile_create())

        return tiles

    async def _get_board_tiles(self, game_id: str) -> list[Tile]:
        """Get all board tiles for a game."""
        cursor = self.database.tiles.find({"game_id": game_id}).sort("position", 1)

        tiles = []
        async for tile_doc in cursor:
            tile_doc["type"] = TileType(tile_doc["type"])
            tile_document = TileDocument.model_validate(tile_doc)
            tiles.append(tile_document.to_tile())

        return tiles
