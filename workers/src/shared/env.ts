import { z } from "zod";

const Env = z.object({
  STDB_URL: z.string().url().default("http://127.0.0.1:3100"),
  STDB_MODULE: z.string().default("sastaspace"),
  STDB_TOKEN: z.string().min(1, "STDB_TOKEN required for owner reducer calls"),

  OLLAMA_URL: z.string().url().default("http://127.0.0.1:11434"),
  OLLAMA_MODEL: z.string().default("gemma3:1b"),
  LOCALAI_URL: z.string().url().default("http://127.0.0.1:8080"),
  LOCALAI_AUDIO_PATH: z.string().default("/v1/audio/speech"),
  LOCALAI_AUDIO_MODEL: z.string().default("tts-1"),
  LOCALAI_AUDIO_VOICE: z.string().default("en-us-amy-low"),

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
