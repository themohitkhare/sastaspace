"""Plan-drafting via Ollama.

Takes the user's project description + desired track count, returns a list of
:class:`PlannedTrack` records. Each record carries a MusicGen prompt that the
generation step feeds straight into the model.

Ollama is reused from the host's existing infra (the comment moderator already
runs an Ollama instance on the prod box). When Ollama isn't reachable, falls
back to a deterministic domain-aware draft so the service stays usable in
local dev / CI without extra setup.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

log = logging.getLogger("sastaspace.deck.plan")

DEFAULT_OLLAMA_MODEL = "gemma3:1b"


@dataclass
class PlannedTrack:
    name: str
    type: str
    length: int
    desc: str
    tempo: str
    instruments: str
    mood: str

    @property
    def musicgen_prompt(self) -> str:
        return (
            f"{self.mood}, {self.type}, {self.tempo}, {self.length}s, "
            f"{self.instruments or 'pad'} — for {self.desc or 'a project'}"
        )


def draft_plan(
    description: str,
    count: int,
    *,
    ollama_url: str | None = None,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    agent: object | None = None,
) -> list[PlannedTrack]:
    """Return ``count`` :class:`PlannedTrack` records for ``description``.

    Tries the Agno-wrapped Ollama agent first when ``ollama_url`` is set or
    a pre-built ``agent`` is passed. Any failure (network, parse error,
    model unavailable) falls back to :func:`_local_draft`, which mirrors
    the frontend's domain-aware seed list.

    Tests pass a mock ``agent`` to exercise the happy path without standing
    up Ollama.
    """
    n = max(1, min(10, count))
    if agent is None and ollama_url:
        try:
            from .agent import AudioPlannerAgent

            agent = AudioPlannerAgent(model_id=ollama_model, ollama_host=ollama_url)
        except Exception as exc:  # noqa: BLE001 — import errors, agno init issues
            log.warning("agent init failed, falling back to local: %s", exc)
            agent = None
    if agent is not None:
        try:
            tracks = agent.plan(description, n)  # type: ignore[attr-defined]
            if tracks:
                return tracks[:n]
        except Exception as exc:  # noqa: BLE001 — covers AgentPlanError + network
            log.warning("agent draft failed, falling back to local: %s", exc)
    return _local_draft(description, n)


def _local_draft(description: str, n: int) -> list[PlannedTrack]:
    """Deterministic, domain-aware fallback that mirrors the frontend logic.

    Keeping a parallel implementation here means the service still produces a
    reasonable plan when called from cURL or tests without the frontend, and
    it documents the canonical seed lists in one place per language.
    """
    lower = description.lower()
    is_meditation = bool(re.search(r"\b(meditation|mindful|sleep|calm|relax|yoga)\b", lower))
    is_game = bool(re.search(r"\b(game|platformer|rpg|puzzle|level|boss|pixel|2d|3d)\b", lower))
    is_video = bool(re.search(r"\b(video|trailer|ad|spot|commercial|product|demo)\b", lower))
    is_podcast = bool(re.search(r"\b(podcast|intro|outro|episode|host)\b", lower))
    is_finance = bool(re.search(r"\b(finance|fintech|dashboard|analytics|trading|wealth)\b", lower))
    is_app = bool(re.search(r"\b(app|mobile|web|onboarding|notification|button|ui)\b", lower)) or is_meditation

    mood = "focused"
    if is_meditation:
        mood = "calm"
    elif is_game:
        mood = "playful"
    elif is_video:
        mood = "cinematic"
    elif is_podcast:
        mood = "warm"
    elif is_finance:
        mood = "focused"
    # Stem-prefix matches (no trailing \b) so "haunted", "nostalgic",
    # "energetic", "dreamy" all trigger their respective overrides.
    if re.search(r"\b(dark|tense|haunt|spook|grim)", lower):
        mood = "dark"
    if re.search(r"\b(warm|nostalg|cozy|gentle)", lower):
        mood = "warm"
    if re.search(r"\b(upbeat|energ|fast|hype)", lower):
        mood = "upbeat"
    if re.search(r"\b(dream|float|airy)", lower):
        mood = "dreamy"

    if is_app or is_meditation or is_finance:
        seeds = [
            ("Background ambient bed", "background", 60, "long-form ambient bed for the home/landing screen", "60bpm", "soft pads, sustained synths, no percussion"),
            ("UI background loop", "loop", 12, "looping low-volume motif behind core flows", "90bpm", "gentle plucks, soft bells, very light rhythm"),
            ("Notification chime", "one-shot", 2, "in-app notification — friendly, non-intrusive", "free", "two-note bell, soft mallet, quick decay"),
            ("Success confirmation", "one-shot", 2, "completed action / saved / sent", "free", "rising tone, light harmonic, gentle"),
            ("Error tone", "one-shot", 2, "something went wrong — soft, not alarming", "free", "low fall, muted pad"),
            ("Onboarding intro", "intro", 8, "plays once on first open, sets the tone", "60bpm", "rising pad, single melodic phrase"),
            ("Screen transition", "transition", 3, "short whoosh between major sections", "free", "air sweep, shimmer"),
            ("Loading loop", "loop", 8, "plays during longer waits", "90bpm", "gentle pulse, soft warble"),
            ("Achievement sting", "sting", 3, "milestone celebration", "free", "bright chord stab, rising"),
            ("Outro / closing", "outro", 6, "plays as the user finishes a session", "60bpm", "descending pad, soft resolution"),
        ]
    elif is_game:
        seeds = [
            ("Title theme", "intro", 30, "plays on the main menu — sets the world", "90bpm", "lead synth, drums, atmosphere"),
            ("Exploration loop", "background", 60, "core gameplay bed", "90bpm", "bass, light percussion, melodic motif"),
            ("Combat loop", "background", 30, "fight / encounter music", "120bpm", "driving drums, distorted bass, brass stabs"),
            ("Boss theme", "background", 60, "boss encounter — bigger, heavier", "120bpm", "orchestral hits, choir, percussion"),
            ("Victory sting", "sting", 3, "plays after winning a fight", "free", "rising orchestral chord, bell"),
            ("Defeat sting", "sting", 3, "plays on game-over", "free", "descending minor chord, low brass"),
            ("Menu loop", "loop", 15, "plays in pause/inventory menus", "60bpm", "soft pad, music box"),
            ("Item pickup", "one-shot", 2, "collected coin / gem / item", "free", "sparkle, bell"),
            ("Hit / damage", "one-shot", 2, "enemy or player takes damage", "free", "punchy thud"),
            ("Level complete", "sting", 4, "end of stage celebration", "free", "fanfare, drums"),
        ]
    elif is_podcast:
        seeds = [
            ("Intro theme", "intro", 15, "opening signature for every episode", "90bpm", "acoustic guitar, soft kick, atmosphere"),
            ("Outro theme", "outro", 15, "closing signature", "90bpm", "acoustic guitar, light strings"),
            ("Ad break bumper", "transition", 5, "bumper between content and sponsor read", "free", "short tag, branded"),
            ("Interview bed", "background", 30, "subtle bed under longer interview segments", "60bpm", "soft pad, no melody"),
            ("Pull-quote sting", "sting", 3, "highlights a guest soundbite", "free", "small chord, pluck"),
            ("Episode-end card", "outro", 8, "plays under credits / patreon mentions", "60bpm", "warm pad, light arpeggio"),
        ]
    elif is_video:
        seeds = [
            ("Hero music bed", "background", 30, "main backing track for the spot", "90bpm", "cinematic pad, light percussion, melody"),
            ("Opening sting", "intro", 4, "plays under the logo / first frame", "free", "rising chord, percussive hit"),
            ("Closing sting", "outro", 4, "plays under the end card / CTA", "free", "resolving chord, gentle hit"),
            ("Tagline bumper", "transition", 3, "punctuates the tagline reveal", "free", "snap, shimmer"),
            ("Voiceover bed", "background", 30, "subtle, no melody under VO", "60bpm", "pad, sub bass"),
        ]
    else:
        seeds = [
            ("Background bed", "background", 30, "main long-form audio bed", "90bpm", "pad, soft melody"),
            ("Short loop", "loop", 12, "compact looping motif", "90bpm", "pluck, soft drums"),
            ("Notification tone", "one-shot", 2, "short signal / chime", "free", "bell, mallet"),
            ("Intro sting", "intro", 4, "opening hit", "free", "rising chord"),
            ("Outro sting", "outro", 4, "closing hit", "free", "resolving chord"),
        ]

    out = [
        PlannedTrack(name=s[0], type=s[1], length=s[2], desc=s[3], tempo=s[4], instruments=s[5], mood=mood)
        for s in seeds[:n]
    ]
    while len(out) < n:
        out.append(
            PlannedTrack(
                name=f"Extra track {len(out) + 1}",
                type="loop",
                length=15,
                desc="additional looping motif",
                tempo="90bpm",
                instruments="pad, pluck",
                mood=mood,
            )
        )
    return out
