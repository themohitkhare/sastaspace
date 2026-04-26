/**
 * Vitest specs for deck-agent. Exercises the plan + generate flows against
 * a fake StdbConn so we never need a running SpacetimeDB or LocalAI.
 *
 * Coverage:
 *   1. plan happy path → setPlan called with parsed tracks
 *   2. plan ollama-failure → setPlanFallback called
 *   3. plan parse-failure (bad JSON) → setPlanFallback called
 *   4. generate happy path → setGenerateDone called with the public URL
 *   5. generate localai-failure → setGenerateFailed called
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";

vi.mock("../shared/env.js", () => ({
  env: {
    STDB_URL: "http://stdb-fake/",
    STDB_MODULE: "sastaspace",
    STDB_TOKEN: "fake-token",
    OLLAMA_URL: "http://ollama-fake/",
    OLLAMA_MODEL: "gemma3:1b",
    LOCALAI_URL: "http://localai-fake/",
    DECK_OUT_DIR: path.join(os.tmpdir(), "deck-out-test"),
    DECK_PUBLIC_BASE_URL: "https://deck.sastaspace.com",
    LOG_LEVEL: "info",
  },
}));

// Mock the shared mastra provider so Agent doesn't try to dial Ollama at
// import time. The deck-agent's planner is overridden via the test seam
// in `start(db, overrides)`, so this mock only has to satisfy import.
vi.mock("../shared/mastra.js", () => ({
  ollamaProvider: () => () => ({}),
}));

vi.mock("@mastra/core/agent", () => ({
  Agent: vi.fn().mockImplementation(() => ({
    generate: vi.fn(),
  })),
}));

type Track = {
  name: string;
  type: string;
  length: number;
  desc: string;
  tempo: string;
  instruments: string;
  mood: string;
};

const samplePlanRow = {
  id: 1n,
  description: "A meditation app for stressed professionals",
  count: 3,
  status: "pending",
};

const sampleGenRow = {
  id: 7n,
  plan_request_id: 1n,
  tracks_json: JSON.stringify([
    {
      name: "Pad",
      type: "background",
      length: 4,
      desc: "bed",
      tempo: "60bpm",
      instruments: "soft pads",
      mood: "calm",
    },
  ]),
  status: "pending",
};

type FakeReducers = {
  setPlan: ReturnType<typeof vi.fn>;
  setPlanFallback: ReturnType<typeof vi.fn>;
  setPlanFailed: ReturnType<typeof vi.fn>;
  setGenerateDone: ReturnType<typeof vi.fn>;
  setGenerateFailed: ReturnType<typeof vi.fn>;
};

function makeFakeDb(
  planRows: Array<typeof samplePlanRow>,
  genRows: Array<typeof sampleGenRow>,
): { db: unknown; reducers: FakeReducers } {
  const reducers: FakeReducers = {
    setPlan: vi.fn(),
    setPlanFallback: vi.fn(),
    setPlanFailed: vi.fn(),
    setGenerateDone: vi.fn(),
    setGenerateFailed: vi.fn(),
  };
  const db = {
    connection: {
      subscriptionBuilder: () => ({ subscribe: vi.fn() }),
      reducers,
      db: {
        planRequest: {
          onInsert: vi.fn(),
          iter: () => planRows,
          id: {
            find: (id: bigint) => planRows.find((r) => r.id === id) ?? null,
          },
        },
        generateJob: {
          onInsert: vi.fn(),
          iter: () => genRows,
        },
      },
    },
    callReducer: vi.fn(),
    subscribe: vi.fn(),
    close: vi.fn(),
  };
  return { db, reducers };
}

const validTracks: Track[] = [
  {
    name: "Pad",
    type: "background",
    length: 60,
    desc: "bed",
    tempo: "60bpm",
    instruments: "soft pads",
    mood: "calm",
  },
  {
    name: "Loop",
    type: "loop",
    length: 12,
    desc: "ui",
    tempo: "90bpm",
    instruments: "plucks",
    mood: "calm",
  },
  {
    name: "Chime",
    type: "one-shot",
    length: 2,
    desc: "notify",
    tempo: "free",
    instruments: "bell",
    mood: "calm",
  },
];

// Shorter wait — tests only need the microtask queue to flush, not real
// timers. 30 ms is enough for the chained Promise.then handlers.
const flush = (): Promise<void> => new Promise((r) => setTimeout(r, 50));

describe("deck-agent", () => {
  let outDir: string;

  beforeEach(async () => {
    vi.clearAllMocks();
    outDir = path.join(os.tmpdir(), "deck-out-test");
    await fs.rm(outDir, { recursive: true, force: true });
  });

  afterEach(async () => {
    await fs.rm(outDir, { recursive: true, force: true });
  });

  it("plan happy path: parsed tracks → setPlan called", async () => {
    const { db, reducers } = makeFakeDb([samplePlanRow], []);
    const { start } = await import("./deck-agent.js");
    const stop = await start(db as never, {
      draftPlan: vi.fn().mockResolvedValue(validTracks),
    });
    await flush();
    expect(reducers.setPlan).toHaveBeenCalledTimes(1);
    expect(reducers.setPlan.mock.calls[0][0]).toBe(1n);
    const written = JSON.parse(reducers.setPlan.mock.calls[0][1] as string);
    expect(written).toHaveLength(3);
    expect(written[0].mood).toBe("calm");
    expect(reducers.setPlanFallback).not.toHaveBeenCalled();
    await stop();
  });

  it("plan failure: ollama throws → setPlanFallback called", async () => {
    const { db, reducers } = makeFakeDb([samplePlanRow], []);
    const { start } = await import("./deck-agent.js");
    const stop = await start(db as never, {
      draftPlan: vi.fn().mockRejectedValue(new Error("ollama down")),
    });
    await flush();
    expect(reducers.setPlan).not.toHaveBeenCalled();
    expect(reducers.setPlanFallback).toHaveBeenCalledTimes(1);
    expect(reducers.setPlanFallback).toHaveBeenCalledWith(1n);
    await stop();
  });

  it("plan parse failure: bad JSON from agent → setPlanFallback called", async () => {
    const { db, reducers } = makeFakeDb([samplePlanRow], []);
    const { start, parseTracks } = await import("./deck-agent.js");
    // The draftPlan seam is the real planner.generate() pipeline; emulate
    // its parse step throwing by routing through the same parseTracks helper
    // the real agent uses.
    const stop = await start(db as never, {
      draftPlan: vi.fn().mockImplementation(async () => parseTracks("not a json array", 3)),
    });
    await flush();
    expect(reducers.setPlan).not.toHaveBeenCalled();
    expect(reducers.setPlanFallback).toHaveBeenCalledWith(1n);
    await stop();
  });

  it("generate happy path: render returns wav → setGenerateDone called with url", async () => {
    const { db, reducers } = makeFakeDb([samplePlanRow], [sampleGenRow]);
    const wav = Buffer.from("RIFF\x00\x00\x00\x00WAVE", "binary");
    const renderTrack = vi.fn().mockResolvedValue(wav);
    const { start } = await import("./deck-agent.js");
    const stop = await start(db as never, {
      // Stub planner so the plan_request row also moves but we don't care here
      draftPlan: vi.fn().mockResolvedValue(validTracks),
      renderTrack,
    });
    await flush();
    expect(renderTrack).toHaveBeenCalledTimes(1);
    expect(reducers.setGenerateDone).toHaveBeenCalledTimes(1);
    expect(reducers.setGenerateDone.mock.calls[0][0]).toBe(7n);
    expect(reducers.setGenerateDone.mock.calls[0][1]).toBe(
      "https://deck.sastaspace.com/7.zip",
    );
    // Zip actually written to disk.
    const written = await fs.readFile(path.join(outDir, "7.zip"));
    expect(written.length).toBeGreaterThan(0);
    expect(reducers.setGenerateFailed).not.toHaveBeenCalled();
    await stop();
  });

  it("generate failure: render throws → setGenerateFailed called", async () => {
    const { db, reducers } = makeFakeDb([], [sampleGenRow]);
    const renderTrack = vi
      .fn()
      .mockRejectedValue(new Error("localai 500: backend missing"));
    const { start } = await import("./deck-agent.js");
    const stop = await start(db as never, {
      draftPlan: vi.fn().mockResolvedValue(validTracks),
      renderTrack,
    });
    await flush();
    expect(reducers.setGenerateDone).not.toHaveBeenCalled();
    expect(reducers.setGenerateFailed).toHaveBeenCalledTimes(1);
    expect(reducers.setGenerateFailed.mock.calls[0][0]).toBe(7n);
    expect(String(reducers.setGenerateFailed.mock.calls[0][1])).toContain(
      "localai 500",
    );
    await stop();
  });
});
