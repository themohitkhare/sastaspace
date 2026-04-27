import { z } from "zod";

const Env = z.object({
  STDB_URL: z.string().url().default("http://127.0.0.1:3100"),
  STDB_MODULE: z.string().default("sastaspace"),
  STDB_TOKEN: z.string().min(1, "STDB_TOKEN required for owner reducer calls"),

  OLLAMA_URL: z.string().url().default("http://127.0.0.1:11434"),
  OLLAMA_MODEL: z.string().default("gemma3:1b"),

  // Deck planner backend. `gemini` (default) calls Google Generative
  // Language REST. `ollama` falls back to the local gemma model — kept
  // for offline dev. Both emit the same JSON schema (PLANNER_INSTRUCTIONS).
  DECK_PLANNER_BACKEND: z.enum(["gemini", "ollama"]).default("gemini"),
  GEMINI_API_KEY: z.string().optional(),
  GEMINI_MODEL: z.string().default("gemini-2.5-flash"),

  LOCALAI_URL: z.string().url().default("http://127.0.0.1:8080"),
  LOCALAI_AUDIO_PATH: z.string().default("/v1/audio/speech"),
  LOCALAI_AUDIO_MODEL: z.string().default("tts-1"),
  LOCALAI_AUDIO_VOICE: z.string().default("en-us-amy-low"),

  // ACE-Step 1.5 standalone API (real text-to-music). Set
  // DECK_AUDIO_BACKEND=acestep to switch the renderer. Default stays on
  // LocalAI/piper TTS so a misconfigured ACE-Step host doesn't take down
  // the deck pipeline.
  DECK_AUDIO_BACKEND: z.enum(["tts", "acestep"]).default("tts"),
  ACESTEP_URL: z.string().url().default("http://127.0.0.1:8001"),
  ACESTEP_MODEL: z.string().default("acestep-v15-turbo"),
  ACESTEP_AUDIO_FORMAT: z.enum(["wav", "mp3", "flac", "ogg"]).default("wav"),
  ACESTEP_INFERENCE_STEPS: z.coerce.number().int().min(1).max(200).default(8),
  ACESTEP_TIMEOUT_MS: z.coerce.number().int().min(10_000).default(180_000),

  // Deck-agent (Phase 1 W3) — output paths for the renderer + zipper.
  // DECK_OUT_DIR is host-mounted into the container at this path; nginx (or
  // a sibling container) serves it at DECK_PUBLIC_BASE_URL.
  DECK_OUT_DIR: z.string().default("/app/deck-out"),
  DECK_PUBLIC_BASE_URL: z.string().url().default("https://deck.sastaspace.com"),

  RESEND_API_KEY: z.string().optional(),
  RESEND_FROM: z.string().default("hi@sastaspace.com"),

  WORKER_AUTH_MAILER_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_ADMIN_COLLECTOR_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_DECK_AGENT_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_MODERATOR_AGENT_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),

  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

export type Env = z.infer<typeof Env>;
export const env: Env = Env.parse(process.env);
