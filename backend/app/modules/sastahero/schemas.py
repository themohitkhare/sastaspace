"""SastaHero Pydantic schemas."""

from enum import Enum

from pydantic import BaseModel


class HeroClass(str, Enum):
    WARRIOR = "WARRIOR"
    MAGE = "MAGE"
    ROGUE = "ROGUE"
    RANGER = "RANGER"
    NECRO = "NECRO"
    PALADIN = "PALADIN"


class StatBlock(BaseModel):
    STR: int
    DEX: int
    INT: int
    WIS: int
    VIT: int
    LCK: int


class ClassDefinition(BaseModel):
    id: HeroClass
    name: str
    icon: str
    desc: str
    base_stats: StatBlock


class HeroResponse(BaseModel):
    hero_class: HeroClass
    stats: StatBlock
    total_power: int


class GenerateRequest(BaseModel):
    hero_class: HeroClass | None = None
