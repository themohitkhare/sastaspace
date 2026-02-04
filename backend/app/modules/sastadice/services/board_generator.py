"""Board generator - creates game boards with special tile placement."""

import random
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.sastadice.services.board_layout import BoardLayout

from app.modules.sastadice.schemas import PROPERTY_COLORS, Tile, TileCreate, TileType


class GameConfig:
    """Dynamic economy scaling based on board size."""

    def __init__(self, num_tiles: int, num_players: int):
        self.num_tiles = num_tiles
        self.num_players = num_players

    @property
    def starting_cash(self) -> int:
        """Starting cash scales with board size: 10 tiles = $750, 25 tiles = $1875."""
        return self.num_tiles * 75

    @property
    def go_bonus(self) -> int:
        """GO bonus scales with board size: 10 tiles = $100, 25 tiles = $250."""
        return self.num_tiles * 10

    @property
    def base_property_price(self) -> int:
        """Base property price scales with board size."""
        return self.num_tiles * 15

    @property
    def base_rent(self) -> int:
        """Base rent is 25% of property price."""
        return self.base_property_price // 4

    def get_tile_price(self, tile_type: TileType, position: int) -> int:
        """Calculate price for a tile based on type and position."""
        if tile_type not in (TileType.PROPERTY, TileType.NODE):
            return 0

        if tile_type == TileType.NODE:
            return 200  # Fixed price for nodes

        position_multiplier = 1.0 + (position / self.num_tiles) * 0.5
        return int(self.base_property_price * position_multiplier)

    def get_tile_rent(self, tile_type: TileType, position: int) -> int:
        """Calculate rent for a tile based on type and position."""
        if tile_type == TileType.NODE:
            return 50  # Base rent (calculated dynamically)
        if tile_type != TileType.PROPERTY:
            return 0

        price = self.get_tile_price(tile_type, position)
        return price // 4


class BoardGenerator:
    """Generates game boards with special tile placement."""

    def __init__(self, board_layout: "BoardLayout") -> None:
        self.layout = board_layout

    def generate_seeded_tiles_for_player(
        self, player_name: str, existing_players: list[Any]
    ) -> list[TileCreate]:
        """Generate 5 seeded tiles for a player joining the game."""
        existing_names = set()
        for player in existing_players:
            for tile in getattr(player, "submitted_tiles", []):
                existing_names.add(tile.name.lower())

        seeded_tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"{player_name}'s Property 1"),
            TileCreate(type=TileType.PROPERTY, name=f"{player_name}'s Property 2"),
            TileCreate(type=TileType.CHANCE, name=f"{player_name}'s Chance"),
            TileCreate(type=TileType.TAX, name=f"{player_name}'s Tax"),
            TileCreate(type=TileType.BUFF, name=f"{player_name}'s Buff"),
        ]

        return seeded_tiles

    def generate_additional_tiles(self, needed: int, player_tiles: list[Tile]) -> list[Tile]:
        """Generate additional tiles to supplement player tiles."""
        generated_tiles = []
        player_names = {tile.name.lower() for tile in player_tiles}

        tile_templates = {
            TileType.PROPERTY: [
                "Park Avenue",
                "Broadway",
                "Fifth Avenue",
                "Times Square",
                "Central Park",
                "Wall Street",
                "Madison Avenue",
                "Lexington Avenue",
                "Park Place",
                "Marvin Gardens",
                "Ventnor Avenue",
                "Atlantic Avenue",
                "Pacific Avenue",
                "North Carolina",
                "Pennsylvania Avenue",
                "Illinois Avenue",
            ],
            TileType.CHANCE: [
                "Community Chest",
                "Lucky Draw",
                "Free Parking",
                "Go to Go",
                "Collect $200",
                "Advance to Boardwalk",
                "Bank Dividend",
                "Life Insurance Matures",
                "Holiday Fund",
                "Income Tax Refund",
                "Beauty Contest",
                "Stock Sale",
            ],
            TileType.TAX: [
                "Income Tax",
                "Luxury Tax",
                "Property Tax",
                "Sales Tax",
                "City Tax",
                "Federal Tax",
                "State Tax",
                "Inheritance Tax",
            ],
            TileType.TRAP: [
                "Go to Jail",
                "Speeding Fine",
                "Parking Violation",
                "Court Fee",
                "Medical Bill",
                "Repair Bill",
                "School Tax",
                "Hospital Fee",
            ],
            TileType.BUFF: [
                "Pass Go Bonus",
                "Birthday Gift",
                "Stock Dividend",
                "Insurance Payout",
                "Lottery Win",
                "Bonus Pay",
                "Tax Refund",
                "Cash Advance",
            ],
        }

        # Exclude special tiles that are placed by _place_special_tiles
        excluded_types = {
            TileType.NEUTRAL,
            TileType.GO,
            TileType.NODE,
            TileType.GO_TO_JAIL,
            TileType.JAIL,
            TileType.TELEPORT,
            TileType.MARKET,
        }
        available_types = [t for t in TileType if t not in excluded_types]

        for i in range(needed):
            tile_type = available_types[i % len(available_types)]
            templates = tile_templates.get(tile_type, [])

            name = None
            attempts = 0
            while name is None or name.lower() in player_names:
                if templates and attempts < len(templates):
                    name = f"{templates[attempts % len(templates)]} {i // len(templates) + 1}"
                else:
                    name = f"{tile_type.value} Tile {i + 1}"
                attempts += 1
                if attempts > 50:
                    name = f"{tile_type.value} {i + 1000}"
                    break

            generated_tiles.append(
                Tile(
                    type=tile_type,
                    name=name,
                    effect_config={},
                    id=str(uuid.uuid4()),
                )
            )
            player_names.add(name.lower())

        return generated_tiles

    def generate_board(
        self,
        player_tiles: list[Tile],
        board_size: int,
        padding: int,
        game_config: GameConfig | None = None,
    ) -> list[Tile]:
        """Generate a closed loop board from player tiles."""
        shuffled_tiles = player_tiles.copy()
        random.shuffle(shuffled_tiles)

        padding_tiles = [
            Tile(
                type=TileType.NEUTRAL,
                name="Empty Space",
                effect_config={},
                id=f"neutral-{i}",
            )
            for i in range(padding)
        ]

        if padding > 0:
            interleaved = self._interleave_tiles(shuffled_tiles, padding_tiles)
        else:
            interleaved = shuffled_tiles

        go_tile = Tile(
            type=TileType.GO,
            name="GO",
            effect_config={"bonus": 200},
            id=str(uuid.uuid4()),
        )
        interleaved.insert(0, go_tile)

        board = self.layout.map_tiles_to_perimeter(interleaved, board_size)
        total_tiles = len(board)

        if total_tiles >= 8:
            # Place special corner tiles
            self._place_special_tiles(board, total_tiles)

        if game_config:
            for tile in board:
                tile.price = game_config.get_tile_price(tile.type, tile.position)
                tile.rent = game_config.get_tile_rent(tile.type, tile.position)

        self._assign_colors(board)

        return board

    def _place_special_tiles(self, board: list[Tile], total_tiles: int) -> None:
        """Place special tiles (Glitch, Jail, Market, GO_TO_JAIL, NODE)."""
        protected = self.layout.get_protected_positions(total_tiles)

        # Place The Glitch at 25%
        glitch_pos = total_tiles // 4
        board[glitch_pos] = Tile(
            type=TileType.TELEPORT,
            name="THE GLITCH",
            effect_config={},
            id=str(uuid.uuid4()),
            position=glitch_pos,
            x=board[glitch_pos].x,
            y=board[glitch_pos].y,
        )

        # Place Server Downtime at 50%
        jail_pos = total_tiles // 2
        board[jail_pos] = Tile(
            type=TileType.JAIL,
            name="SERVER DOWNTIME",
            effect_config={},
            id=str(uuid.uuid4()),
            position=jail_pos,
            x=board[jail_pos].x,
            y=board[jail_pos].y,
        )

        # Place Black Market at 75%
        market_pos = (total_tiles * 3) // 4
        board[market_pos] = Tile(
            type=TileType.MARKET,
            name="BLACK MARKET",
            effect_config={},
            id=str(uuid.uuid4()),
            position=market_pos,
            x=board[market_pos].x,
            y=board[market_pos].y,
        )

        # Place 404: ACCESS DENIED before Black Market
        self._place_go_to_jail_tile(board, total_tiles, protected)

        # Place NODE tiles at side midpoints
        self._place_node_tiles(board, total_tiles, protected)

    def _place_go_to_jail_tile(
        self, board: list[Tile], total_tiles: int, protected: set[int]
    ) -> None:
        """Place 404: ACCESS DENIED tile before Black Market."""
        # Position just before Black Market (75% - 2)
        pos = (total_tiles * 3) // 4 - 2
        while pos in protected:
            pos -= 1
        if pos < 0:
            pos = 1

        board[pos] = Tile(
            type=TileType.GO_TO_JAIL,
            name="404: ACCESS DENIED",
            effect_config={},
            id=str(uuid.uuid4()),
            position=pos,
            x=board[pos].x,
            y=board[pos].y,
        )

    def _place_node_tiles(self, board: list[Tile], total_tiles: int, protected: set[int]) -> None:
        """Place 4 NODE tiles at side midpoints, avoiding corners."""
        # Calculate midpoints of each side (between corners)
        midpoints = [
            total_tiles // 8,  # Top side
            total_tiles * 3 // 8,  # Right side
            total_tiles * 5 // 8,  # Bottom side
            total_tiles * 7 // 8,  # Left side
        ]

        node_names = ["NODE_ALPHA", "NODE_BETA", "NODE_GAMMA", "NODE_DELTA"]

        for i, pos in enumerate(midpoints):
            # Adjust if collision with protected position
            while pos in protected:
                pos = (pos + 1) % total_tiles

            board[pos] = Tile(
                type=TileType.NODE,
                name=node_names[i],
                id=str(uuid.uuid4()),
                position=pos,
                x=board[pos].x,
                y=board[pos].y,
                price=200,  # Fixed price for nodes
                rent=50,  # Base rent (calculated dynamically)
            )

    def _assign_colors(self, board: list[Tile]) -> None:
        """Assign colors to property tiles in groups of 2-3."""
        properties = [t for t in board if t.type == TileType.PROPERTY]
        if not properties:
            return

        set_size = 2 if len(properties) <= 8 else 3

        for i, prop in enumerate(properties):
            color_index = (i // set_size) % len(PROPERTY_COLORS)
            prop.color = PROPERTY_COLORS[color_index]

    def _interleave_tiles(self, player_tiles: list[Tile], padding_tiles: list[Tile]) -> list[Tile]:
        """Interleave padding tiles evenly among player tiles."""
        result = []
        player_idx = 0
        padding_idx = 0
        total_tiles = len(player_tiles) + len(padding_tiles)

        spacing = len(player_tiles) // len(padding_tiles) if len(padding_tiles) > 0 else total_tiles

        for i in range(total_tiles):
            if padding_idx < len(padding_tiles) and i > 0 and i % (spacing + 1) == 0:
                result.append(padding_tiles[padding_idx])
                padding_idx += 1
            elif player_idx < len(player_tiles):
                result.append(player_tiles[player_idx])
                player_idx += 1

        while player_idx < len(player_tiles):
            result.append(player_tiles[player_idx])
            player_idx += 1
        while padding_idx < len(padding_tiles):
            result.append(padding_tiles[padding_idx])
            padding_idx += 1

        return result
