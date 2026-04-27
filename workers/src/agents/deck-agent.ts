/**
 * deck-agent — Mastra+Ollama planner + LocalAI MusicGen renderer.
 *
 * Subscribes to:
 *   - plan_request WHERE status='pending'  → drafts a track plan via Ollama,
 *     calls setPlan on success or setPlanFallback on any failure (the reducer
 *     synthesizes the deterministic fallback from description+count).
 *   - generate_job WHERE status='pending'  → renders each track via LocalAI's
 *     MusicGen sound-generation endpoint, zips WAVs + a README.txt onto the
 *     host-mounted /app/deck-out volume, calls setGenerateDone with the
 *     public URL. On any failure calls setGenerateFailed.
 *
 * The worker keeps in-flight sets to avoid double-processing the same row
 * across an `iter()` snapshot + onInsert race.
 */

import { promises as fs } from "node:fs";
import path from "node:path";

import { Agent } from "@mastra/core/agent";
import JSZip from "jszip";

import { env } from "../shared/env.js";
import { ollamaProvider } from "../shared/mastra.js";
import type { StdbConn } from "../shared/stdb.js";

const log = (level: string, msg: string, extra?: unknown): void => {
  console.log(JSON.stringify({
    ts: new Date().toISOString(),
    agent: "deck-agent",
    level,
    msg,
    extra,
  }));
};

// 1:1 port of services/deck/src/sastaspace_deck/agent.py:PLANNER_INSTRUCTIONS.
// Kept verbatim so a model swap doesn't silently change drafting behaviour.
export const PLANNER_INSTRUCTIONS = `You are a music director for a small audio-asset tool.

Given a project description and a target track count, output a JSON array of
exactly that many tracks. Each track is an object with these exact keys:

- name        (string, short title, sentence case)
- type        (one of: background, loop, one-shot, intro, outro, transition, sting, jingle)
- length      (integer seconds, 1..180)
- desc        (string, one-sentence usage hint)
- tempo       (one of: 60bpm, 90bpm, 120bpm, free)
- instruments (string, comma-separated, e.g. "soft pads, gentle bell, no percussion")
- mood        (one of: calm, focused, playful, cinematic, dark, upbeat, warm, tense, dreamy, nostalgic)

Pick a mood that matches the project. Pick types that cover the project's
real audio needs (e.g. an app needs a notification, a game needs combat
music). Keep durations realistic — notifications are 2s, beds are 30-60s.

Output ONLY the JSON array. No prose, no markdown, no code fences, no
explanations. Start with \`[\` and end with \`]\`.
`;

export type Track = {
  name: string;
  type: string;
  length: number;
  desc: string;
  tempo: string;
  instruments: string;
  mood: string;
};

type PlanRow = {
  id: bigint;
  description: string;
  count: number;
  status: string;
};

// SDK 2.1 generates camelCase row fields from the snake_case Rust struct.
type GenRow = {
  id: bigint;
  tracksJson: string;
  planRequestId: bigint | null;
  status: string;
};

// Internal seam so tests can swap the renderer / planner without touching
// network. The real worker uses the defaults; tests override via
// `__test_overrides`.
type Deps = {
  draftPlan(description: string, count: number): Promise<Track[]>;
  renderTrack(track: Track): Promise<Buffer>;
};

export async function start(
  db: StdbConn,
  overrides?: Partial<Deps>,
): Promise<() => Promise<void>> {
  const conn = (db as unknown as { connection: StdbAccessor }).connection;

  // Lazy provider so env vars resolve at start() time. Two planner backends:
  // `gemini` (default, calls the Generative Language REST API) and `ollama`
  // (kept as fallback so the deck still drafts plans if Gemini is reachable
  // at all). Both produce the same JSON schema downstream of parseTracks.
  const ollamaPlanner = new Agent({
    name: "deck-planner",
    instructions: PLANNER_INSTRUCTIONS,
    model: ollamaProvider()(env.OLLAMA_MODEL),
  });

  const draftPlanViaOllama = async (description: string, count: number): Promise<Track[]> => {
    const resp = await ollamaPlanner.generate(
      `project description:\n${description}\n\ntrack count: ${count}\n\nReturn the JSON array now.`,
    );
    const text = typeof resp.text === "string" ? resp.text.trim() : "";
    return parseTracks(text, count);
  };

  const deps: Deps = {
    draftPlan:
      overrides?.draftPlan ??
      (async (description, count) => {
        if (env.DECK_PLANNER_BACKEND === "gemini") {
          try {
            return await draftPlanViaGemini(description, count);
          } catch (e) {
            log("warn", "gemini planner failed, falling back to ollama", { error: String(e) });
            return draftPlanViaOllama(description, count);
          }
        }
        return draftPlanViaOllama(description, count);
      }),
    renderTrack: overrides?.renderTrack ?? renderTrack,
  };

  // Some SDK shapes return a builder, some return the subscription handle
  // directly. Wrap in try so missing methods (e.g. test stubs) don't crash.
  try {
    const builder = conn.subscriptionBuilder?.();
    builder?.subscribe?.([
      "SELECT * FROM plan_request WHERE status = 'pending'",
      "SELECT * FROM generate_job WHERE status = 'pending'",
    ]);
  } catch (e) {
    log("warn", "subscriptionBuilder unavailable", { error: String(e) });
  }

  // SDK 2.1 exposes table accessors with snake_case keys (e.g. `plan_request`)
  // not camelCase. Rebind via Record for type-safe access.
  const dbAny = conn.db as unknown as Record<string, {
    onInsert?: (cb: (ctx: unknown, row: unknown) => void) => void;
    iter?: () => Iterable<unknown>;
    id?: { find?: (id: bigint) => { description: string } | undefined };
  }>;
  const planRequestTable = dbAny.plan_request;
  const generateJobTable = dbAny.generate_job;

  const planInFlight = new Set<string>();
  const genInFlight = new Set<string>();

  // ---------- plan handling ----------
  const handlePlan = async (row: PlanRow): Promise<void> => {
    const key = row.id.toString();
    if (planInFlight.has(key)) return;
    planInFlight.add(key);
    try {
      const tracks = await deps.draftPlan(row.description, row.count);
      // SDK 2.1: reducer args are a single object literal with camelCase keys
      // matching the Rust reducer parameter names.
      (conn.reducers as unknown as {
        setPlan: (a: { requestId: bigint; tracksJson: string }) => void;
      }).setPlan({ requestId: row.id, tracksJson: JSON.stringify(tracks) });
      log("info", "plan set", { id: key, count: tracks.length });
    } catch (e) {
      log("warn", "planner failed → fallback", { id: key, error: String(e) });
      try {
        (conn.reducers as unknown as {
          setPlanFallback: (a: { requestId: bigint }) => void;
        }).setPlanFallback({ requestId: row.id });
      } catch (innerErr) {
        log("error", "setPlanFallback also failed", {
          id: key,
          error: String(innerErr),
        });
      }
    } finally {
      planInFlight.delete(key);
    }
  };

  if (planRequestTable?.onInsert) {
    planRequestTable.onInsert((_ctx, row) => {
      const r = row as PlanRow;
      if (r.status === "pending") void handlePlan(r);
    });
  }
  if (planRequestTable?.iter) {
    for (const row of planRequestTable.iter()) {
      const r = row as PlanRow;
      if (r.status === "pending") void handlePlan(r);
    }
  }

  // ---------- generate handling ----------
  const handleGenerate = async (row: GenRow): Promise<void> => {
    const key = row.id.toString();
    if (genInFlight.has(key)) return;
    genInFlight.add(key);
    try {
      const tracks = JSON.parse(row.tracksJson) as Track[];
      if (!Array.isArray(tracks) || tracks.length === 0) {
        throw new Error("tracksJson empty");
      }

      const zip = new JSZip();
      const usedNames = new Set<string>();

      for (let i = 0; i < tracks.length; i++) {
        const t = tracks[i];
        const wav = await deps.renderTrack(t);
        const filename = uniqueFilename(t.name, i + 1, usedNames);
        zip.file(filename, wav);
      }

      // Pull the description back out for the README. If the row references a
      // plan_request, use that description; otherwise use a synthetic line.
      let description = "(ad-hoc plan, no source plan_request)";
      if (row.planRequestId != null && planRequestTable?.id?.find) {
        const pr = planRequestTable.id.find(row.planRequestId);
        if (pr) description = pr.description;
      }
      zip.file("README.txt", buildReadme(description, tracks));

      const bytes = await zip.generateAsync({
        type: "nodebuffer",
        compression: "DEFLATE",
      });
      const filename = `${row.id.toString()}.zip`;
      const outDir = env.DECK_OUT_DIR;
      await fs.mkdir(outDir, { recursive: true });
      await fs.writeFile(path.join(outDir, filename), bytes);

      const url = `${env.DECK_PUBLIC_BASE_URL.replace(/\/$/, "")}/${filename}`;
      (conn.reducers as unknown as {
        setGenerateDone: (a: { jobId: bigint; zipUrl: string }) => void;
      }).setGenerateDone({ jobId: row.id, zipUrl: url });
      log("info", "generate done", {
        id: key,
        url,
        bytes: bytes.length,
      });
    } catch (e) {
      log("error", "generate failed", { id: key, error: String(e) });
      try {
        (conn.reducers as unknown as {
          setGenerateFailed: (a: { jobId: bigint; error: string }) => void;
        }).setGenerateFailed({ jobId: row.id, error: String(e).slice(0, 400) });
      } catch (innerErr) {
        log("error", "setGenerateFailed also failed", {
          id: key,
          error: String(innerErr),
        });
      }
    } finally {
      genInFlight.delete(key);
    }
  };

  if (generateJobTable?.onInsert) {
    generateJobTable.onInsert((_ctx, row) => {
      const r = row as GenRow;
      if (r.status === "pending") void handleGenerate(r);
    });
  }
  if (generateJobTable?.iter) {
    for (const row of generateJobTable.iter()) {
      const r = row as GenRow;
      if (r.status === "pending") void handleGenerate(r);
    }
  }

  log("info", "deck-agent started", {
    ollama: env.OLLAMA_URL,
    localai: env.LOCALAI_URL,
    deckOut: env.DECK_OUT_DIR,
  });
  return async () => {
    log("info", "deck-agent stopping");
  };
}

// ---------- helpers ----------

/**
 * Parse the agent's text into validated tracks. Tolerates ```json fences.
 * Mirrors services/deck/src/sastaspace_deck/agent.py:_parse_tracks.
 */
export function parseTracks(raw: string, count: number): Track[] {
  if (!raw) throw new Error("empty agent response");
  let text = raw;
  if (text.startsWith("```")) {
    const parts = text.split("```");
    if (parts.length >= 3) {
      let inner = parts[1];
      if (inner.startsWith("json")) inner = inner.slice(4);
      text = inner;
    }
  }
  text = text.trim();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (e) {
    throw new Error(`agent output not valid JSON: ${String(e)}`);
  }
  if (!Array.isArray(data)) throw new Error("agent output not a JSON array");
  const out: Track[] = [];
  for (const row of data.slice(0, count)) {
    if (!row || typeof row !== "object") continue;
    const r = row as Record<string, unknown>;
    if (
      typeof r.name !== "string" ||
      typeof r.type !== "string" ||
      typeof r.length !== "number"
    ) {
      continue;
    }
    out.push({
      name: String(r.name).slice(0, 80),
      type: String(r.type).slice(0, 24),
      length: Math.max(1, Math.min(180, Math.round(Number(r.length)))),
      desc: typeof r.desc === "string" ? r.desc.slice(0, 240) : "",
      tempo: typeof r.tempo === "string" ? r.tempo.slice(0, 24) : "90bpm",
      instruments:
        typeof r.instruments === "string" ? r.instruments.slice(0, 240) : "",
      mood: typeof r.mood === "string" ? r.mood.slice(0, 24) : "focused",
    });
  }
  if (out.length === 0) throw new Error("no parseable tracks in agent output");
  return out;
}

/**
 * Gemini planner via the Generative Language REST API. We deliberately
 * skip the @google/genai SDK so the workers image stays slim and our
 * type surface stays just `fetch + zod-shape parseTracks`.
 *
 * Returns the parsed Track[] (or throws so the caller can fall back to
 * Ollama or call setPlanFallback). The PLANNER_INSTRUCTIONS constant
 * keeps the schema requirements in one place; we inline it as a system
 * instruction so Gemini emits raw JSON without code fences.
 */
export async function draftPlanViaGemini(
  description: string,
  count: number,
): Promise<Track[]> {
  if (!env.GEMINI_API_KEY) {
    throw new Error("GEMINI_API_KEY not set");
  }
  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(env.GEMINI_MODEL)}:generateContent` +
    `?key=${encodeURIComponent(env.GEMINI_API_KEY)}`;
  const body = {
    systemInstruction: { parts: [{ text: PLANNER_INSTRUCTIONS }] },
    contents: [
      {
        role: "user",
        parts: [
          {
            text: `project description:\n${description}\n\ntrack count: ${count}\n\nReturn the JSON array now.`,
          },
        ],
      },
    ],
    generationConfig: {
      temperature: 0.7,
      responseMimeType: "application/json",
    },
  };
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    throw new Error(`gemini ${r.status}: ${(await r.text()).slice(0, 200)}`);
  }
  const j = (await r.json()) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  };
  const text = j.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";
  if (!text) throw new Error(`gemini returned empty body: ${JSON.stringify(j).slice(0, 200)}`);
  return parseTracks(text, count);
}

// Audio backend selector. `tts` calls LocalAI piper at /v1/audio/speech
// (narrated description, default since 2026-04-27). `acestep` calls
// ACE-Step 1.5's standalone async API (real music; runs natively on ROCm
// per AMD's official guide — bypasses the broken LocalAI wrappers).
export async function renderTrack(t: Track): Promise<Buffer> {
  if (env.DECK_AUDIO_BACKEND === "acestep") return renderViaAceStep(t);
  return renderViaLocalAi(t);
}

export async function renderViaLocalAi(t: Track): Promise<Buffer> {
  const prompt = buildMusicgenPrompt(t);
  const path = env.LOCALAI_AUDIO_PATH;
  const model = env.LOCALAI_AUDIO_MODEL;
  const url = `${env.LOCALAI_URL.replace(/\/$/, "")}${path}`;
  const body: Record<string, unknown> = { model, input: prompt };
  if (path === "/v1/sound-generation") body.duration = t.length;
  if (path === "/v1/audio/speech") body.voice = env.LOCALAI_AUDIO_VOICE;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`localai ${r.status}: ${detail.slice(0, 200)}`);
  }
  const ab = await r.arrayBuffer();
  return Buffer.from(ab);
}

/**
 * ACE-Step 1.5 standalone API client. The server is async-only:
 *  1. POST /release_task with the prompt + duration → returns task_id.
 *  2. Poll POST /query_result with [task_id] until status === 1 (success)
 *     or 2 (failed). Times out at ACESTEP_TIMEOUT_MS to bound retries.
 *  3. The success result contains audio file paths on the server's disk;
 *     pull the first one via GET /v1/audio?path=... and return its bytes.
 *
 * Reference: docs/en/API.md in ace-step/ACE-Step-1.5.
 */
export async function renderViaAceStep(t: Track): Promise<Buffer> {
  const base = env.ACESTEP_URL.replace(/\/$/, "");
  const prompt = buildMusicgenPrompt(t);

  // Step 1: kick off generation.
  const releaseBody: Record<string, unknown> = {
    prompt,
    audio_duration: Math.max(10, t.length),
    audio_format: env.ACESTEP_AUDIO_FORMAT,
    inference_steps: env.ACESTEP_INFERENCE_STEPS,
    batch_size: 1,
    use_random_seed: true,
  };
  if (env.ACESTEP_MODEL) releaseBody.model = env.ACESTEP_MODEL;
  const releaseRes = await fetch(`${base}/release_task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(releaseBody),
  });
  if (!releaseRes.ok) {
    throw new Error(
      `acestep release_task ${releaseRes.status}: ${(await releaseRes.text()).slice(0, 200)}`,
    );
  }
  const releaseJson = (await releaseRes.json()) as {
    code: number;
    error: string | null;
    data: { task_id?: string };
  };
  const taskId = releaseJson.data?.task_id;
  if (!taskId) {
    throw new Error(`acestep release_task: no task_id in ${JSON.stringify(releaseJson).slice(0, 200)}`);
  }

  // Step 2: poll until done.
  const deadline = Date.now() + env.ACESTEP_TIMEOUT_MS;
  let resultJsonStr: string | null = null;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 2000));
    const qr = await fetch(`${base}/query_result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id_list: [taskId] }),
    });
    if (!qr.ok) continue;
    const j = (await qr.json()) as {
      data: Array<{ task_id: string; status: number; result: string }>;
    };
    const row = j.data?.[0];
    if (row?.status === 1) {
      resultJsonStr = row.result;
      break;
    }
    if (row?.status === 2) {
      throw new Error(`acestep task ${taskId} failed: ${row.result}`);
    }
  }
  if (!resultJsonStr) {
    throw new Error(`acestep task ${taskId} did not complete in ${env.ACESTEP_TIMEOUT_MS}ms`);
  }

  // Step 3: parse result, find the audio reference, then download. ACE-Step
  // returns each item's `file` already as `/v1/audio?path=<urlencoded>` —
  // the URL path is ready to append to the base host.
  const parsed = JSON.parse(resultJsonStr) as unknown;
  const audioPathOrUrl = extractAudioReference(parsed);
  if (!audioPathOrUrl) {
    throw new Error(`acestep result has no audio reference: ${resultJsonStr.slice(0, 200)}`);
  }
  const audioUrl = audioPathOrUrl.startsWith("/v1/audio")
    ? `${base}${audioPathOrUrl}`
    : `${base}/v1/audio?path=${encodeURIComponent(audioPathOrUrl)}`;
  const audioRes = await fetch(audioUrl);
  if (!audioRes.ok) {
    throw new Error(`acestep /v1/audio ${audioRes.status} for ${audioPathOrUrl}`);
  }
  return Buffer.from(await audioRes.arrayBuffer());
}

// Walk a parsed query_result `result` payload and return the first
// plausible audio reference. ACE-Step uses `{ file: "/v1/audio?path=..." }`
// as the canonical handle; raw filesystem paths or wave-buffer hex are
// fallback shapes worth tolerating.
function extractAudioReference(parsed: unknown): string | undefined {
  const seen = new Set<unknown>();
  const stack: unknown[] = [parsed];
  while (stack.length) {
    const v = stack.pop();
    if (!v || seen.has(v)) continue;
    seen.add(v);
    if (typeof v === "string") {
      if (v.startsWith("/v1/audio")) return v;
      if (/\.(wav|mp3|flac|ogg)(\?|$)/i.test(v)) return v;
    }
    if (Array.isArray(v)) {
      for (const item of v) stack.push(item);
    } else if (typeof v === "object") {
      for (const item of Object.values(v as Record<string, unknown>)) stack.push(item);
    }
  }
  return undefined;
}

export function buildMusicgenPrompt(t: Track): string {
  return `${t.mood}, ${t.type}, ${t.tempo}, ${t.length}s, ${
    t.instruments || "pad"
  } — for ${t.desc || "a project"}`;
}

// 1:1 port of services/deck/src/sastaspace_deck/main.py:_readme.
export function buildReadme(description: string, plan: Track[]): string {
  const lines = [
    "deck — sastaspace audio designer",
    "================================",
    "",
    `brief: ${description}`,
    "",
    "tracks:",
  ];
  plan.forEach((t, i) => {
    const idx = String(i + 1).padStart(2, "0");
    lines.push(`  ${idx}. ${t.name} — ${t.type} · ${t.mood} · ${t.length}s`);
    lines.push(`      ${buildMusicgenPrompt(t)}`);
  });
  lines.push("");
  lines.push("license: cc-by 4.0");
  return lines.join("\n");
}

const SLUG_RE = /[^a-z0-9]+/g;
export function slugify(s: string): string {
  const cleaned = s
    .toLowerCase()
    .replace(SLUG_RE, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 30);
  return cleaned || "track";
}

export function uniqueFilename(
  name: string,
  idx: number,
  used: Set<string>,
): string {
  const base = slugify(name);
  let candidate = `${String(idx).padStart(2, "0")}-${base}.wav`;
  if (used.has(candidate)) {
    candidate = `${String(idx).padStart(2, "0")}-${base}-${idx}.wav`;
  }
  used.add(candidate);
  return candidate;
}

// ---------- StdbConn shape used by deck-agent ----------
//
// The W1 stdb.ts stub doesn't yet expose `connection`, `db`, `reducers` —
// those land when W1 wires the real @clockworklabs/spacetimedb-sdk. This
// interface documents what the deck-agent uses so a future change to
// stdb.ts can be type-checked against it.
//
// We type these as `any`-ish dynamic accessors so the agent compiles before
// W1's bindings land; the smoke test will fail fast if the real shape
// diverges from the assumed camelCase accessors.

interface StdbAccessor {
  subscriptionBuilder?(): { subscribe?(queries: string[]): unknown } | undefined;
  reducers: {
    setPlan(requestId: bigint, tracksJson: string): void;
    setPlanFallback(requestId: bigint): void;
    setPlanFailed?(requestId: bigint, error: string): void;
    setGenerateDone(jobId: bigint, zipUrl: string): void;
    setGenerateFailed(jobId: bigint, error: string): void;
  };
  db: {
    planRequest?: {
      onInsert?(cb: (ctx: unknown, row: PlanRow) => void): void;
      iter?(): Iterable<PlanRow>;
      id?: { find(id: bigint): { description: string } | undefined };
    };
    generateJob?: {
      onInsert?(cb: (ctx: unknown, row: GenRow) => void): void;
      iter?(): Iterable<GenRow>;
    };
  };
}
