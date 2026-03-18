"""SastaHero API router — card game endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_db
from app.modules.sastahero.schemas import (
    CardInstance,
    CollectionResponse,
    KnowledgeResponse,
    PlayerProfile,
    PowerupResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizQuestionResponse,
    ShardBalance,
    StageResponse,
    StoryResponse,
    SwipeRequest,
    SwipeResponse,
)
from app.modules.sastahero.services import (
    complete_stage,
    get_collection,
    get_knowledge,
    get_profile,
    get_quiz_question,
    get_shards,
    get_story,
    process_swipe,
    purchase_powerup,
    reroll_card,
    submit_quiz_answer,
)
from app.modules.sastahero.services import (
    generate_stage as generate_stage_service,
)

router = APIRouter()


@router.get("/stage", response_model=StageResponse)
async def get_stage(
    player_id: str = Query(..., description="Player UUID"),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> StageResponse:
    """Generate next 10-card stage for player."""
    return await generate_stage_service(db, player_id)


@router.post("/swipe", response_model=SwipeResponse)
async def swipe_card(
    request: SwipeRequest,
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> SwipeResponse:
    """Process a swipe action on a card."""
    return await process_swipe(db, request.player_id, request.card_id, request.action.value)


@router.post("/stage/{stage_number}/complete")
async def mark_stage_complete(
    stage_number: int,
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> dict[str, Any]:
    """Mark a stage as completed and check milestones."""
    return await complete_stage(db, player_id, stage_number)


@router.get("/quiz", response_model=QuizQuestionResponse)
async def get_quiz(
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> QuizQuestionResponse:
    """Get a quiz question between stages."""
    return await get_quiz_question(db, player_id)


@router.post("/quiz/answer", response_model=QuizAnswerResponse)
async def answer_quiz(
    request: QuizAnswerRequest,
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> QuizAnswerResponse:
    """Submit quiz answer and get rewards."""
    return await submit_quiz_answer(
        db,
        request.player_id,
        request.question_id,
        request.selected_index,
        request.time_taken_ms,
    )


@router.get("/collection", response_model=CollectionResponse)
async def get_player_collection(
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> CollectionResponse:
    """Get player's collection book."""
    return await get_collection(db, player_id)


@router.get("/shards", response_model=ShardBalance)
async def get_player_shards(
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> ShardBalance:
    """Get current shard balances."""
    return await get_shards(db, player_id)


@router.post("/powerup", response_model=PowerupResponse)
async def buy_powerup(
    request: dict[str, Any],
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> PowerupResponse:
    """Purchase a powerup with shards."""
    player_id = request.get("player_id", "")
    powerup_type = request.get("powerup_type", "")
    shard_type = request.get("shard_type")
    if not player_id or not powerup_type:
        raise HTTPException(status_code=422, detail="player_id and powerup_type required")
    return await purchase_powerup(db, player_id, powerup_type, shard_type)


@router.post("/reroll", response_model=CardInstance | None)
async def reroll(
    request: dict[str, Any],
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> CardInstance | None:
    """Reroll a card (requires Reroll powerup)."""
    player_id = request.get("player_id", "")
    card_id = request.get("card_id", "")
    if not player_id or not card_id:
        raise HTTPException(status_code=422, detail="player_id and card_id required")
    result = await reroll_card(db, player_id, card_id)
    if result is None:
        raise HTTPException(status_code=400, detail="No reroll powerup or card not found")
    return result


@router.get("/story", response_model=StoryResponse)
async def get_player_story(
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> StoryResponse:
    """Get player's story thread."""
    return await get_story(db, player_id)


@router.get("/knowledge", response_model=KnowledgeResponse)
async def get_player_knowledge(
    player_id: str = Query(...),
    category: str | None = Query(None),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> KnowledgeResponse:
    """Get player's knowledge bank."""
    return await get_knowledge(db, player_id, category)


@router.get("/profile", response_model=PlayerProfile)
async def get_player_profile(
    player_id: str = Query(...),
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
) -> PlayerProfile:
    """Get player profile and stats."""
    return await get_profile(db, player_id)
