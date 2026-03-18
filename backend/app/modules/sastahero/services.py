"""SastaHero services — random hero generation."""

import random

from app.modules.sastahero.schemas import (
    ClassDefinition,
    HeroClass,
    HeroResponse,
    StatBlock,
)

CLASS_DEFINITIONS: dict[HeroClass, ClassDefinition] = {
    HeroClass.WARRIOR: ClassDefinition(
        id=HeroClass.WARRIOR,
        name="Warrior",
        icon="⚔️",
        desc="Brute force specialist",
        base_stats=StatBlock(STR=8, DEX=4, INT=2, WIS=3, VIT=8, LCK=5),
    ),
    HeroClass.MAGE: ClassDefinition(
        id=HeroClass.MAGE,
        name="Mage",
        icon="🔮",
        desc="Arcane devastation",
        base_stats=StatBlock(STR=2, DEX=3, INT=9, WIS=7, VIT=4, LCK=5),
    ),
    HeroClass.ROGUE: ClassDefinition(
        id=HeroClass.ROGUE,
        name="Rogue",
        icon="🗡️",
        desc="Shadows and daggers",
        base_stats=StatBlock(STR=4, DEX=9, INT=5, WIS=3, VIT=4, LCK=5),
    ),
    HeroClass.RANGER: ClassDefinition(
        id=HeroClass.RANGER,
        name="Ranger",
        icon="🏹",
        desc="Nature's marksman",
        base_stats=StatBlock(STR=5, DEX=7, INT=4, WIS=6, VIT=5, LCK=3),
    ),
    HeroClass.NECRO: ClassDefinition(
        id=HeroClass.NECRO,
        name="Necromancer",
        icon="💀",
        desc="Death is just the beginning",
        base_stats=StatBlock(STR=3, DEX=3, INT=8, WIS=8, VIT=3, LCK=5),
    ),
    HeroClass.PALADIN: ClassDefinition(
        id=HeroClass.PALADIN,
        name="Paladin",
        icon="🛡️",
        desc="Holy tank",
        base_stats=StatBlock(STR=6, DEX=3, INT=4, WIS=6, VIT=8, LCK=3),
    ),
}

# Stat weights per class for random allocation (higher = more likely to receive bonus points)
CLASS_STAT_WEIGHTS: dict[HeroClass, dict[str, int]] = {
    HeroClass.WARRIOR: {"STR": 5, "DEX": 2, "INT": 1, "WIS": 1, "VIT": 4, "LCK": 2},
    HeroClass.MAGE: {"STR": 1, "DEX": 1, "INT": 5, "WIS": 4, "VIT": 2, "LCK": 2},
    HeroClass.ROGUE: {"STR": 2, "DEX": 5, "INT": 2, "WIS": 2, "VIT": 2, "LCK": 4},
    HeroClass.RANGER: {"STR": 2, "DEX": 4, "INT": 2, "WIS": 3, "VIT": 3, "LCK": 2},
    HeroClass.NECRO: {"STR": 1, "DEX": 1, "INT": 4, "WIS": 5, "VIT": 2, "LCK": 2},
    HeroClass.PALADIN: {"STR": 3, "DEX": 1, "INT": 2, "WIS": 4, "VIT": 5, "LCK": 2},
}

BONUS_POINTS = 30
STAT_MAX = 20


def get_all_classes() -> list[ClassDefinition]:
    return list(CLASS_DEFINITIONS.values())


def generate_random_hero(hero_class: HeroClass | None = None) -> HeroResponse:
    if hero_class is None:
        hero_class = random.choice(list(HeroClass))

    class_def = CLASS_DEFINITIONS[hero_class]
    weights = CLASS_STAT_WEIGHTS[hero_class]
    stat_names = list(weights.keys())
    weight_values = list(weights.values())

    # Start from base stats
    stats = class_def.base_stats.model_dump()

    # Distribute 30 bonus points with class-appropriate weighting
    remaining = BONUS_POINTS
    while remaining > 0:
        chosen = random.choices(stat_names, weights=weight_values, k=1)[0]
        if stats[chosen] < STAT_MAX:
            stats[chosen] += 1
            remaining -= 1

    stat_block = StatBlock(**stats)
    total_power = sum(stats.values())

    return HeroResponse(
        hero_class=hero_class,
        stats=stat_block,
        total_power=total_power,
    )
