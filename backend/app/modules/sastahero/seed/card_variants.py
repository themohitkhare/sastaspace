"""Seed card variants — story fragments, knowledge, and resources for all 31 identities."""

# Each variant: (identity_id, content_type, text, category)
# Story cards have no category. Knowledge cards have category. Resource cards have no text.

CARD_VARIANTS: list[tuple[str, str, str, str | None]] = [
    # ── Common: Genesis (Creation) ──
    ("genesis", "STORY", "From the silence, something stirred—", None),
    ("genesis", "STORY", "A seed broke through ash-covered earth,", None),
    ("genesis", "STORY", "The first breath echoed across emptiness,", None),
    (
        "genesis",
        "KNOWLEDGE",
        "The oldest known living organism is a bristlecone pine, over 5,000 years old.",
        "science",
    ),
    ("genesis", "RESOURCE", "", None),
    # ── Common: Aegis (Protection) ──
    ("aegis", "STORY", "Walls rose where none had stood before,", None),
    ("aegis", "STORY", "An unseen shield hummed against the storm,", None),
    ("aegis", "STORY", "The guardian's oath was carved in stone,", None),
    (
        "aegis",
        "KNOWLEDGE",
        "The Great Wall of China is not visible from space with the naked eye—a common myth.",
        "history",
    ),
    ("aegis", "RESOURCE", "", None),
    # ── Common: Entropy (Destruction) ──
    ("entropy", "STORY", "The old tower crumbled without warning,", None),
    ("entropy", "STORY", "Fire consumed what time had already forgotten,", None),
    ("entropy", "STORY", "Cracks spread through the foundation like veins,", None),
    (
        "entropy",
        "KNOWLEDGE",
        "Entropy always increases in a closed system—the second law of thermodynamics.",
        "science",
    ),
    ("entropy", "RESOURCE", "", None),
    # ── Common: Spark (Energy) ──
    ("spark", "STORY", "Lightning split the sky in two,", None),
    ("spark", "STORY", "A faint glow pulsed beneath the surface,", None),
    ("spark", "STORY", "The air crackled with unseen potential,", None),
    (
        "spark",
        "KNOWLEDGE",
        "A single bolt of lightning contains enough energy to toast 100,000 slices of bread.",
        "science",
    ),
    ("spark", "RESOURCE", "", None),
    # ── Common: Dominion (Power) ──
    ("dominion", "STORY", "The throne sat empty, waiting for its claim,", None),
    ("dominion", "STORY", "Authority radiated from the ancient seal,", None),
    ("dominion", "STORY", "Every creature in the valley bowed instinctively,", None),
    (
        "dominion",
        "KNOWLEDGE",
        "The word 'power' comes from the Latin 'potere,' meaning 'to be able.'",
        "language",
    ),
    ("dominion", "RESOURCE", "", None),
    # ── Uncommon: Guardian (Creation + Protection) ──
    ("guardian", "STORY", "She built the wall with her own hands, and it held,", None),
    ("guardian", "STORY", "New shields grew from living crystal,", None),
    (
        "guardian",
        "KNOWLEDGE",
        "Coral reefs build their own protective structures from calcium carbonate.",
        "science",
    ),
    ("guardian", "RESOURCE", "", None),
    # ── Uncommon: Rebirth (Creation + Destruction) ──
    ("rebirth", "STORY", "From the ashes, a sprout pushed through,", None),
    ("rebirth", "STORY", "The old world had to end for this one to begin,", None),
    (
        "rebirth",
        "KNOWLEDGE",
        "Forest fires trigger the germination of certain seeds that need extreme heat to crack open.",
        "science",
    ),
    ("rebirth", "RESOURCE", "", None),
    # ── Uncommon: Dawn (Creation + Energy) ──
    ("dawn", "STORY", "The first light carried warmth and promise,", None),
    ("dawn", "STORY", "Energy coalesced into something entirely new,", None),
    (
        "dawn",
        "KNOWLEDGE",
        "The Sun produces enough energy in one second to power Earth for 500,000 years.",
        "science",
    ),
    ("dawn", "RESOURCE", "", None),
    # ── Uncommon: Architect (Creation + Power) ──
    ("architect", "STORY", "The blueprint was drawn in lines of force,", None),
    ("architect", "STORY", "What was imagined became undeniable,", None),
    (
        "architect",
        "KNOWLEDGE",
        "The Great Pyramid of Giza was the tallest structure on Earth for 3,800 years.",
        "history",
    ),
    ("architect", "RESOURCE", "", None),
    # ── Uncommon: Barrier (Protection + Destruction) ──
    ("barrier", "STORY", "The wall held, but barely—cracks spread like lightning,", None),
    ("barrier", "STORY", "Destruction met resistance and shattered against it,", None),
    (
        "barrier",
        "KNOWLEDGE",
        "Earth's magnetic field protects us from solar wind that would otherwise strip away our atmosphere.",
        "science",
    ),
    ("barrier", "RESOURCE", "", None),
    # ── Uncommon: Radiance (Protection + Energy) ──
    ("radiance", "STORY", "Light poured from the shield like liquid gold,", None),
    ("radiance", "STORY", "The barrier hummed with captured sunlight,", None),
    (
        "radiance",
        "KNOWLEDGE",
        "Bioluminescence is used by over 76% of deep-sea creatures for both defense and communication.",
        "science",
    ),
    ("radiance", "RESOURCE", "", None),
    # ── Uncommon: Sentinel (Protection + Power) ──
    ("sentinel", "STORY", "The guardian channeled raw force into an impenetrable stance,", None),
    ("sentinel", "STORY", "Nothing passed the sentinel's gaze unchallenged,", None),
    (
        "sentinel",
        "KNOWLEDGE",
        "Roman Praetorian Guards served as both bodyguards and political powerbrokers.",
        "history",
    ),
    ("sentinel", "RESOURCE", "", None),
    # ── Uncommon: Wildfire (Destruction + Energy) ──
    ("wildfire", "STORY", "Flames danced with impossible speed across the plain,", None),
    ("wildfire", "STORY", "The explosion of light left nothing but echoes,", None),
    (
        "wildfire",
        "KNOWLEDGE",
        "A wildfire can move at speeds up to 14 mph in forests and 40 mph in grasslands.",
        "science",
    ),
    ("wildfire", "RESOURCE", "", None),
    # ── Uncommon: Ruin (Destruction + Power) ──
    ("ruin", "STORY", "The force of the blow reshaped the landscape,", None),
    ("ruin", "STORY", "What once stood tall was reduced to rubble and memory,", None),
    (
        "ruin",
        "KNOWLEDGE",
        "The Tsar Bomba, the most powerful nuclear weapon ever detonated, had a yield of 50 megatons.",
        "history",
    ),
    ("ruin", "RESOURCE", "", None),
    # ── Uncommon: Surge (Energy + Power) ──
    ("surge", "STORY", "Power surged through every circuit and nerve,", None),
    ("surge", "STORY", "The energy wave rippled outward, amplifying everything it touched,", None),
    (
        "surge",
        "KNOWLEDGE",
        "The human brain generates about 20 watts of electrical power—enough to dimly light a bulb.",
        "science",
    ),
    ("surge", "RESOURCE", "", None),
    # ── Rare: Fortress (C+P+D) ──
    ("fortress", "STORY", "Built from ruins, the fortress defied both time and siege,", None),
    (
        "fortress",
        "KNOWLEDGE",
        "The ancient city of Masada withstood Roman siege for three years before falling.",
        "history",
    ),
    ("fortress", "RESOURCE", "", None),
    # ── Rare: Aurora (C+P+E) ──
    ("aurora", "STORY", "Colors danced in the sky, a shield of living light,", None),
    (
        "aurora",
        "KNOWLEDGE",
        "Auroras occur when charged particles from the Sun interact with Earth's magnetosphere.",
        "science",
    ),
    ("aurora", "RESOURCE", "", None),
    # ── Rare: Throne (C+P+Pw) ──
    (
        "throne",
        "STORY",
        "The throne was forged from the mountain itself, unyielding and eternal,",
        None,
    ),
    (
        "throne",
        "KNOWLEDGE",
        "The Peacock Throne of the Mughal Empire was valued at twice the cost of the Taj Mahal.",
        "history",
    ),
    ("throne", "RESOURCE", "", None),
    # ── Rare: Phoenix (C+D+E) ──
    ("phoenix", "STORY", "The bird of flame dissolved and reformed in the same breath,", None),
    (
        "phoenix",
        "KNOWLEDGE",
        "Some species of bacteria can survive extreme radiation by rapidly repairing their own DNA.",
        "science",
    ),
    ("phoenix", "RESOURCE", "", None),
    # ── Rare: Cataclysm (C+D+Pw) ──
    (
        "cataclysm",
        "STORY",
        "The ground split open, and from the chasm rose something terrible and new,",
        None,
    ),
    (
        "cataclysm",
        "KNOWLEDGE",
        "The asteroid that killed the dinosaurs released energy equivalent to 10 billion Hiroshima bombs.",
        "science",
    ),
    ("cataclysm", "RESOURCE", "", None),
    # ── Rare: Nova (C+E+Pw) ──
    (
        "nova",
        "STORY",
        "A star collapsed and bloomed in the same instant, scattering brilliance,",
        None,
    ),
    (
        "nova",
        "KNOWLEDGE",
        "A supernova can briefly outshine an entire galaxy of hundreds of billions of stars.",
        "science",
    ),
    ("nova", "RESOURCE", "", None),
    # ── Rare: Bastion (P+D+E) ──
    ("bastion", "STORY", "The last stronghold burned but did not fall,", None),
    (
        "bastion",
        "KNOWLEDGE",
        "Tardigrades can survive in the vacuum of space, extreme temperatures, and intense radiation.",
        "science",
    ),
    ("bastion", "RESOURCE", "", None),
    # ── Rare: Warden (P+D+Pw) ──
    (
        "warden",
        "STORY",
        "The warden stood where creation and destruction met, holding the line,",
        None,
    ),
    (
        "warden",
        "KNOWLEDGE",
        "The Samurai code of Bushido emphasized both martial prowess and moral duty.",
        "history",
    ),
    ("warden", "RESOURCE", "", None),
    # ── Rare: Beacon (P+E+Pw) ──
    ("beacon", "STORY", "The signal cut through darkness, a pillar of unwavering light,", None),
    (
        "beacon",
        "KNOWLEDGE",
        "The Lighthouse of Alexandria, one of the Seven Wonders, stood for over 1,500 years.",
        "history",
    ),
    ("beacon", "RESOURCE", "", None),
    # ── Rare: Tempest (D+E+Pw) ──
    ("tempest", "STORY", "The storm was alive—each thunderclap a word, each gust a command,", None),
    (
        "tempest",
        "KNOWLEDGE",
        "Jupiter's Great Red Spot is a storm larger than Earth that has raged for over 350 years.",
        "science",
    ),
    ("tempest", "RESOURCE", "", None),
    # ── Epic: Eclipse (C+P+D+E) ──
    ("eclipse", "STORY", "When sun met shadow, the world held its breath and was remade,", None),
    (
        "eclipse",
        "KNOWLEDGE",
        "A total solar eclipse can cause temperatures to drop by as much as 10°F in minutes.",
        "science",
    ),
    ("eclipse", "RESOURCE", "", None),
    # ── Epic: Oblivion (C+P+D+Pw) ──
    ("oblivion", "STORY", "Memory itself was forged into a weapon and a shield,", None),
    (
        "oblivion",
        "KNOWLEDGE",
        "The Library of Alexandria's destruction erased an estimated 400,000 scrolls of ancient knowledge.",
        "history",
    ),
    ("oblivion", "RESOURCE", "", None),
    # ── Epic: Ascension (C+P+E+Pw) ──
    (
        "ascension",
        "STORY",
        "The climb ended not at a peak, but at the edge of understanding,",
        None,
    ),
    (
        "ascension",
        "KNOWLEDGE",
        "Mount Everest grows approximately 4mm taller each year due to tectonic forces.",
        "geography",
    ),
    ("ascension", "RESOURCE", "", None),
    # ── Epic: Maelstrom (C+D+E+Pw) ──
    ("maelstrom", "STORY", "Everything converged into a single, impossible point of chaos,", None),
    (
        "maelstrom",
        "KNOWLEDGE",
        "Black holes can spin at nearly the speed of light, warping spacetime around them.",
        "science",
    ),
    ("maelstrom", "RESOURCE", "", None),
    # ── Epic: Nexus (P+D+E+Pw) ──
    ("nexus", "STORY", "All forces met at the crossroads, neither yielding nor advancing,", None),
    (
        "nexus",
        "KNOWLEDGE",
        "The human brain has approximately 86 billion neurons, each forming up to 10,000 connections.",
        "science",
    ),
    ("nexus", "RESOURCE", "", None),
    # ── Legendary: Singularity (all 5) ──
    (
        "singularity",
        "STORY",
        "Every thread of existence wove into one shimmering point of convergence,",
        None,
    ),
    (
        "singularity",
        "KNOWLEDGE",
        "The observable universe contains an estimated 2 trillion galaxies, each with billions of stars.",
        "science",
    ),
    ("singularity", "RESOURCE", "", None),
]
