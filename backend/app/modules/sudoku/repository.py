"""MongoDB repository for Sudoku matches and AI state."""

from __future__ import annotations

import pickle
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.sudoku import genetic


class SudokuRepository:
    """CRUD for ``sudoku_matches`` and ``sudoku_ai_state`` collections."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._matches = db["sudoku_matches"]
        self._ai = db["sudoku_ai_state"]

    # -- Matches --------------------------------------------------------

    async def create_match(self, doc: dict[str, Any]) -> None:
        await self._matches.insert_one(doc)

    async def get_match(self, match_id: str) -> dict[str, Any] | None:
        doc = await self._matches.find_one({"match_id": match_id})
        return doc

    async def update_match(self, match_id: str, update: dict[str, Any]) -> None:
        await self._matches.update_one({"match_id": match_id}, {"$set": update})

    # -- AI State -------------------------------------------------------

    async def create_ai_state(
        self,
        match_id: str,
        population: list[genetic.Chromosome],
        tabu_hashes: list[int],
    ) -> None:
        blob = pickle.dumps((population, tabu_hashes))
        n = len(population[0].rows) if population else 0
        doc: dict[str, Any] = {
            "match_id": match_id,
            "generation_count": 0,
            "stall_count": 0,
            "fitness_score": 0.0,
            "heatmap_data": [0.0] * (n * n),
            "best_board": [0] * (n * n),
            "population_blob": blob,
        }
        await self._ai.insert_one(doc)

    async def get_ai_state(self, match_id: str) -> dict[str, Any] | None:
        doc = await self._ai.find_one({"match_id": match_id})
        return doc

    async def update_ai_state(self, match_id: str, update: dict[str, Any]) -> None:
        await self._ai.update_one({"match_id": match_id}, {"$set": update})

    async def load_population(
        self,
        ai_doc: dict[str, Any],
    ) -> tuple[list[genetic.Chromosome], list[int]]:
        blob: bytes = ai_doc.get("population_blob", b"")
        if not blob:
            return [], []
        return pickle.loads(blob)  # type: ignore[no-any-return]  # noqa: S301

    async def save_population(
        self,
        match_id: str,
        population: list[genetic.Chromosome],
        tabu_hashes: list[int],
    ) -> None:
        blob = pickle.dumps((population, tabu_hashes))
        await self._ai.update_one(
            {"match_id": match_id},
            {"$set": {"population_blob": blob}},
        )
