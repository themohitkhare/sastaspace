"""SastaHero API router."""

from fastapi import APIRouter

from app.modules.sastahero.schemas import (
    ClassDefinition,
    GenerateRequest,
    HeroResponse,
)
from app.modules.sastahero.services import generate_random_hero, get_all_classes

router = APIRouter()


@router.get("/classes", response_model=list[ClassDefinition])
def list_classes() -> list[ClassDefinition]:
    """Return all hero class definitions with base stats."""
    return get_all_classes()


@router.post("/generate", response_model=HeroResponse)
def generate_hero(request: GenerateRequest) -> HeroResponse:
    """Generate a random hero with class-weighted stat allocation."""
    return generate_random_hero(request.hero_class)
