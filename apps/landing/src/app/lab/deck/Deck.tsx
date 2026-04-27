"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { unzipSync } from "fflate";
import styles from "./deck.module.css";
// Phase 2 F4 — STDB-native plan/generate path. Both this and the legacy
// HTTP path coexist behind NEXT_PUBLIC_USE_STDB_DECK; the flag picks one
// at build time. TODO(Phase 4 modularization): once cutover is stable,
// the legacy path + this flag both go away and Deck.tsx splits into
// per-step components (audit M1).
import { useDeckStdb } from "./useDeckStdb";
import {
  submitPlan,
  submitGenerate,
  type Track as StdbTrack,
} from "./deckStdbFlows";

// Set this to the deck service URL to enable real /plan + /generate calls.
// Leave undefined to keep the page in offline-prototype mode (local draft +
// procedural Web Audio playback) — useful in CI builds and on `next build`
// before the service is reachable.
const API_URL = process.env.NEXT_PUBLIC_DECK_API_URL;

// When true, route /plan and /generate through SpacetimeDB reducers
// (Phase 2 F4) instead of the deprecated services/deck HTTP API. Both
// paths coexist until Phase 3 cutover; default false until cutover.
const USE_STDB = process.env.NEXT_PUBLIC_USE_STDB_DECK === "true";

type Phase = "idle" | "planning" | "plan" | "generating" | "results" | "error";

type Track = {
  id: string;
  name: string;
  type: string;
  length: number;
  desc: string;
  tempo: string;
  instruments: string;
  mood: string;
};

type TrackAudio = {
  url: string;
  filename: string;
  blob: Blob;
};

const MAX_TRACKS = 10;

const TYPE_OPTIONS = ["background", "loop", "one-shot", "intro", "outro", "transition", "sting", "jingle"];
const MOOD_OPTIONS = ["calm", "focused", "playful", "cinematic", "dark", "upbeat", "warm", "tense", "dreamy", "nostalgic"];
const LENGTH_OPTIONS = [3, 8, 15, 30, 60, 120];
const TEMPO_OPTIONS = ["60bpm", "90bpm", "120bpm", "free"];

const EXAMPLES: { label: string; prompt: string }[] = [
  {
    label: "meditation app",
    prompt: "A meditation app for stressed professionals. Calm, slow, breathing-paced. Soft pads, no percussion.",
  },
  {
    label: "retro platformer",
    prompt: "A 2D pixel-art platformer set in a haunted candy factory. Playful but slightly off, music-box bells, spooky bass.",
  },
  {
    label: "finance dashboard",
    prompt: "A finance dashboard for a fintech startup. Trustworthy, focused, minimal. Soft synths, clean tones, nothing percussive.",
  },
  {
    label: "product video",
    prompt: "A 30-second product video for a hardware keyboard. Tactile, mechanical, satisfying. Clean lo-fi beat, soft snaps.",
  },
  {
    label: "podcast intro",
    prompt: "A morning-routine podcast intro. Warm, optimistic, slightly nostalgic. Acoustic guitar, light strings.",
  },
];

const RECENTS = [
  {
    when: "· 2 min ago",
    label: "Onboarding flow for a sleep app — slow, dreamy, low pulse.",
    prompt: "Onboarding flow for a sleep app — slow, dreamy, low pulse. Soft pads, gentle chimes.",
  },
  {
    when: "· yesterday",
    label: "Co-op puzzle game, cozy autumn forest setting, woodwinds.",
    prompt: "A co-op puzzle game in a cozy autumn forest. Curious and warm. Woodwinds, plucked strings, light percussion.",
  },
  {
    when: "· last week",
    label: "Walking-tour app for old neighborhoods, warm and curious.",
    prompt: "A walking-tour app for old neighborhoods. Warm, curious, observant. Acoustic, soft brass, no drums.",
  },
];

export function Deck() {
  const [prompt, setPrompt] = useState("");
  const [desiredCount, setDesiredCount] = useState(3);
  const [phase, setPhase] = useState<Phase>("idle");
  const [plan, setPlan] = useState<Track[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [planProgress, setPlanProgress] = useState(0);

  // Phase 2 F4: STDB connection (mounted only when USE_STDB is true) and
  // the plan_request id returned from the STDB plan flow so the subsequent
  // generate flow can cite it (lets the reducer enforce "only the submitter
  // may generate from their own plan").
  const stdb = useDeckStdb(USE_STDB);
  const [stdbPlanId, setStdbPlanId] = useState<bigint | null>(null);

  // Real generated audio: per-track Blob URLs (extracted from the zip
  // returned by /generate or the STDB worker), the zip blob itself for the
  // bulk download button, a status string for the generating phase, and an
  // error string when the pipeline fails.
  const [audioByTrack, setAudioByTrack] = useState<Map<string, TrackAudio> | null>(null);
  const [zipBlob, setZipBlob] = useState<Blob | null>(null);
  const [generateStatus, setGenerateStatus] = useState<string>("");
  const [generateError, setGenerateError] = useState<string | null>(null);

  const promptRef = useRef<HTMLTextAreaElement | null>(null);
  const trimmed = prompt.trim();
  const canPlan = trimmed.length >= 4 && phase !== "planning";

  const stepNum = phase === "idle" ? 1 : phase === "planning" || phase === "plan" ? 2 : 3;

  const onPlan = useCallback(() => {
    if (!canPlan) return;
    setPhase("planning");
    setPlanProgress(0);
    const start = performance.now();
    // Run the API call in parallel with a visible progress animation so the
    // UI doesn't jump straight to step 2. We always wait for both before
    // transitioning — the animation sets a floor on perceived latency.
    const minDur = 1700;

    // ────────── F4: STDB path ──────────
    if (USE_STDB && stdb) {
      let stdbResolvedTracks: Track[] | null = null;
      let stdbResolvedPlanId: bigint | null = null;
      let stdbSettled = false;
      void submitPlan(stdb.conn, stdb.identityHex, trimmed, desiredCount)
        .then((res) => {
          if (res.kind === "done") {
            stdbResolvedTracks = res.tracks.map((t) => ({ id: nextId(), ...t }));
            stdbResolvedPlanId = res.planRequestId;
          } else {
            console.warn(
              "[deck] stdb plan failed, using local draft:",
              res.error,
            );
          }
        })
        .catch((err) => {
          console.warn("[deck] stdb plan threw, using local draft:", err);
        })
        .finally(() => {
          stdbSettled = true;
        });
      const stdbTickId = window.setInterval(() => {
        const r = Math.min((performance.now() - start) / minDur, 1);
        setPlanProgress(r);
        if (r >= 1 && stdbSettled) {
          window.clearInterval(stdbTickId);
          setPlan(stdbResolvedTracks ?? draftPlan(trimmed, desiredCount));
          setStdbPlanId(stdbResolvedPlanId);
          setPhase("plan");
          setOpenId(null);
        }
      }, 60);
      return;
    }

    // ────────── legacy: HTTP path ──────────
    let resolvedTracks: Track[] | null = null;
    let apiSettled = !API_URL; // when there's no API, treat the call as "done"
    if (API_URL) {
      void fetchPlan(API_URL, trimmed, desiredCount)
        .then((tracks) => {
          resolvedTracks = tracks;
        })
        .catch((err) => {
          console.warn("[deck] /plan failed, using local draft:", err);
        })
        .finally(() => {
          apiSettled = true;
        });
    }
    const id = window.setInterval(() => {
      const r = Math.min((performance.now() - start) / minDur, 1);
      setPlanProgress(r);
      if (r >= 1 && apiSettled) {
        window.clearInterval(id);
        setPlan(resolvedTracks ?? draftPlan(trimmed, desiredCount));
        setPhase("plan");
        setOpenId(null);
      }
    }, 60);
  }, [canPlan, trimmed, desiredCount, stdb]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        onPlan();
      }
    },
    [onPlan],
  );

  // Free any per-track Object URLs we hold so the browser can release the
  // underlying blob memory. Called whenever we discard the previous result
  // set (new generate, reset, unmount).
  const revokeAudio = useCallback(() => {
    setAudioByTrack((prev) => {
      if (prev) prev.forEach(({ url }) => URL.revokeObjectURL(url));
      return null;
    });
    setZipBlob(null);
  }, []);

  const reset = useCallback(() => {
    revokeAudio();
    setPrompt("");
    setPlan([]);
    setOpenId(null);
    setPhase("idle");
    setPlanProgress(0);
    setGenerateStatus("");
    setGenerateError(null);
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  }, [revokeAudio]);

  const onClear = useCallback(() => {
    revokeAudio();
    setPrompt("");
    setPhase("idle");
    setPlan([]);
    setOpenId(null);
    setGenerateError(null);
  }, [revokeAudio]);

  // ── real /generate flow ──
  // Run only when phase is "generating": call the backend (STDB or HTTP),
  // fetch the zip, unpack it client-side into per-track Blob URLs, then
  // transition to "results". Any failure flips phase to "error" with a
  // message — the user sees the truth, not a fake animation that lies
  // about progress.
  useEffect(() => {
    if (phase !== "generating") return;
    let cancelled = false;

    const run = async () => {
      // Revoke any previous URLs and clear state. setState inside an
      // async callback is fine — only synchronous-in-effect-body is
      // flagged by react-hooks/set-state-in-effect.
      setAudioByTrack((prev) => {
        if (prev) prev.forEach(({ url }) => URL.revokeObjectURL(url));
        return null;
      });
      setZipBlob(null);
      setGenerateError(null);
      try {
        setGenerateStatus("rendering audio…");
        let blob: Blob;
        if (USE_STDB) {
          if (!stdb) throw new Error("STDB connection not ready — try again in a moment");
          // Reducer expects camelCase fields without our client-side ids.
          const tracks: StdbTrack[] = plan.map(({ id, ...rest }) => {
            void id;
            return rest;
          });
          const res = await submitGenerate(stdb.conn, stdb.identityHex, stdbPlanId, tracks);
          if (cancelled) return;
          if (res.kind !== "done") throw new Error(res.error || "generate failed");
          const r = await fetch(res.zipUrl);
          if (!r.ok) throw new Error(`zip fetch failed: ${r.status}`);
          blob = await r.blob();
        } else if (API_URL) {
          blob = await fetchGenerate(API_URL, trimmed, plan);
        } else {
          throw new Error(
            "deck is not configured: set NEXT_PUBLIC_DECK_API_URL or NEXT_PUBLIC_USE_STDB_DECK=true",
          );
        }
        if (cancelled) return;
        setGenerateStatus("unpacking tracks…");
        const map = await unpackZipToTracks(blob, plan);
        if (cancelled) {
          map.forEach(({ url }) => URL.revokeObjectURL(url));
          return;
        }
        setZipBlob(blob);
        setAudioByTrack(map);
        setGenerateStatus("");
        setPhase("results");
      } catch (err) {
        if (cancelled) return;
        console.warn("[deck] generate failed:", err);
        setGenerateError(err instanceof Error ? err.message : String(err));
        setGenerateStatus("");
        setPhase("error");
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // Free per-track URLs when the component unmounts.
  useEffect(() => {
    return () => {
      if (audioByTrack) {
        audioByTrack.forEach(({ url }) => URL.revokeObjectURL(url));
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onExample = useCallback((p: string) => {
    setPrompt(p);
    setPhase("idle");
    promptRef.current?.focus();
  }, []);

  const updateTrack = useCallback((id: string, patch: Partial<Track>) => {
    setPlan((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  }, []);

  const removeTrack = useCallback((id: string) => {
    setPlan((prev) => prev.filter((t) => t.id !== id));
    setOpenId((cur) => (cur === id ? null : cur));
  }, []);

  const duplicateTrack = useCallback((id: string) => {
    setPlan((prev) => {
      if (prev.length >= MAX_TRACKS) return prev;
      const i = prev.findIndex((t) => t.id === id);
      if (i < 0) return prev;
      const t = prev[i];
      const copy: Track = { ...t, id: nextId(), name: `${t.name} (copy)` };
      const next = prev.slice();
      next.splice(i + 1, 0, copy);
      return next;
    });
  }, []);

  const addTrack = useCallback(() => {
    setPlan((prev) => {
      if (prev.length >= MAX_TRACKS) return prev;
      const fresh = blankTrack();
      setOpenId(fresh.id);
      return [...prev, fresh];
    });
  }, []);

  const totalSec = plan.reduce((s, t) => s + t.length, 0);
  const estZipMb = useMemo(() => Math.max(0.1, totalSec * 0.18).toFixed(1), [totalSec]);
  const estGenTime = useMemo(() => {
    const sec = plan.reduce((s, t) => s + Math.max(8, t.length * 1.2), 0);
    if (sec < 60) return `${Math.round(sec)}s`;
    return `${Math.round(sec / 60)}m ${Math.round(sec % 60)}s`;
  }, [plan]);

  return (
    <>
      <div className={styles.crumbBar}>
        <div className={styles.crumb}>
          <a href="/lab">~/lab</a>
          <span className={styles.crumbSep}>/</span>
          <span className={styles.crumbHere}>deck</span>
        </div>
      </div>

      <header className={styles.head}>
        <div className={styles.headAnchor}>deck.sastaspace.com —</div>
        <h1>
          Describe a project. <span className={styles.headAccent}>Get audio.</span>
        </h1>
        <p className={styles.headLede}>
          Two stages. First the deck drafts a track list from your description &mdash; you review and edit.
          Then it generates the audio. Up to ten tracks per project, packaged as a zip.
        </p>
        <div className={styles.metaRow}>
          <span className={`${styles.chip} ${styles.chipWip}`}>wip</span>
          <span className={`${styles.chip} ${styles.chipOss}`}>open source</span>
          <div className={styles.tags}>
            <span className={styles.tag}>musicgen</span>
            <span className={styles.tag}>ollama</span>
            <span className={styles.tag}>cpu-ok</span>
          </div>
        </div>
      </header>

      <Stepper step={stepNum} />

      {phase === "idle" && (
        <>
          <Composer
            value={prompt}
            onChange={setPrompt}
            onKeyDown={onKeyDown}
            promptRef={promptRef}
            count={desiredCount}
            setCount={setDesiredCount}
            onPlan={onPlan}
            onClear={onClear}
            canPlan={canPlan}
          />
          <div className={styles.examples}>
            <span className={styles.examplesLab}>try one →</span>
            {EXAMPLES.map((ex) => (
              <button key={ex.label} type="button" onClick={() => onExample(ex.prompt)}>
                {ex.label}
              </button>
            ))}
          </div>
          <Recents onReplay={onExample} />
        </>
      )}

      {phase !== "idle" && (
        <section className={styles.panel} aria-live="polite">
          {phase === "planning" && (
            <PlanningCard prompt={trimmed} count={desiredCount} progress={planProgress} />
          )}
          {phase === "plan" && (
            <PlanView
              prompt={trimmed}
              plan={plan}
              openId={openId}
              setOpenId={setOpenId}
              onUpdate={updateTrack}
              onRemove={removeTrack}
              onDuplicate={duplicateTrack}
              onAdd={addTrack}
              onBack={() => setPhase("idle")}
              onRedraft={onPlan}
              onGenerate={() => setPhase("generating")}
              totalSec={totalSec}
              estZipMb={estZipMb}
              estGenTime={estGenTime}
            />
          )}
          {phase === "generating" && (
            <GeneratingView plan={plan} status={generateStatus} />
          )}
          {phase === "error" && (
            <ErrorView
              error={generateError ?? "unknown error"}
              onRetry={() => setPhase("generating")}
              onBack={() => setPhase("plan")}
            />
          )}
          {phase === "results" && (
            <Results
              plan={plan}
              estZipMb={estZipMb}
              audioByTrack={audioByTrack}
              zipBlob={zipBlob}
              onEdit={() => setPhase("plan")}
              onNew={reset}
            />
          )}
        </section>
      )}
    </>
  );
}

// ============================================================================
// stepper
// ============================================================================
function Stepper({ step }: { step: number }) {
  const items = [
    { n: 1, name: "describe" },
    { n: 2, name: "plan tracks" },
    { n: 3, name: "generate & download" },
  ];
  return (
    <div className={styles.stepper}>
      {items.map((it, i) => (
        <Fragment key={it.n}>
          <div
            className={`${styles.step} ${
              step === it.n ? styles.stepActive : step > it.n ? styles.stepDone : ""
            }`}
          >
            <span className={styles.stepNum}>{it.n}</span>
            <span className={styles.stepName}>{it.name}</span>
          </div>
          {i < items.length - 1 && <div className={styles.stepDiv} />}
        </Fragment>
      ))}
    </div>
  );
}

// React.Fragment with key support without importing whole namespace
function Fragment({ children }: { key?: number; children: React.ReactNode }) {
  return <>{children}</>;
}

// ============================================================================
// composer (step 1)
// ============================================================================
type ComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  promptRef: React.RefObject<HTMLTextAreaElement | null>;
  count: number;
  setCount: (n: number) => void;
  onPlan: () => void;
  onClear: () => void;
  canPlan: boolean;
};

function Composer({
  value, onChange, onKeyDown, promptRef, count, setCount, onPlan, onClear, canPlan,
}: ComposerProps) {
  return (
    <section className={styles.composer} aria-label="Describe your project">
      <div className={styles.composerLabelRow}>
        <label htmlFor="deck-prompt" className={styles.composerLabel}>describe what you&apos;re building</label>
        <div className={styles.composerCount} aria-hidden="true">{value.length} / 600</div>
      </div>
      <textarea
        ref={promptRef}
        id="deck-prompt"
        value={value}
        maxLength={600}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="A meditation app for stressed professionals. Calm, slow, breathing-paced. Soft pads, no percussion."
        spellCheck={false}
        aria-describedby="deck-prompt-count"
      />
      <span id="deck-prompt-count" className={styles.srOnly} aria-live="polite">
        {value.length} of 600 characters used
      </span>
      <div className={styles.composerActions}>
        <div className={styles.hint}>
          <kbd>⌘</kbd>+<kbd>↵</kbd> to plan tracks &mdash; ollama runs in ~3 s
        </div>
        <div className={styles.countRow}>
          <span className={styles.countLab}>draft</span>
          <div className={styles.stepperInput}>
            <button
              type="button"
              onClick={() => setCount(Math.max(1, count - 1))}
              disabled={count <= 1}
              aria-label="decrease track count"
            >
              −
            </button>
            <span className={styles.stepperVal}>{count}</span>
            <button
              type="button"
              onClick={() => setCount(Math.min(MAX_TRACKS, count + 1))}
              disabled={count >= MAX_TRACKS}
              aria-label="increase track count"
            >
              +
            </button>
          </div>
          <span className={styles.countLab}>tracks</span>
          <button className={`${styles.btn} ${styles.btnGhost}`} type="button" onClick={onClear}>
            clear
          </button>
          <button
            className={`${styles.btn} ${styles.btnPrimary}`}
            type="button"
            onClick={onPlan}
            disabled={!canPlan}
          >
            <span>plan tracks</span>
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
              <path
                d="M3 8 L13 8 M9 4 L13 8 L9 12"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// recents
// ============================================================================
function Recents({ onReplay }: { onReplay: (p: string) => void }) {
  return (
    <section className={styles.recents}>
      <div className={styles.recentsHeadRow}>
        <h3>Recently on the deck</h3>
        <span className={styles.recentsCount}>{RECENTS.length} generations</span>
      </div>
      <ul className={styles.recentsList}>
        {RECENTS.map((r) => (
          <li key={r.label}>
            <span className={styles.recentsWhen}>{r.when}</span>
            <span className={styles.recentsLabel}>{r.label}</span>
            <button className={styles.replay} type="button" onClick={() => onReplay(r.prompt)}>
              replay →
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ============================================================================
// planning card (transient)
// ============================================================================
function PlanningCard({
  prompt, count, progress,
}: {
  prompt: string;
  count: number;
  progress: number;
}) {
  return (
    <div className={`${styles.genCard} ${styles.fadeIn}`}>
      <div className={styles.genHead}>
        <div className={styles.genTitle}>
          drafting a track plan&hellip;
          <span className={styles.liveBars} aria-hidden="true">
            <span /><span /><span /><span /><span />
          </span>
        </div>
        <div className={styles.genHeadRight}>ollama</div>
      </div>
      <div className={styles.genPrompt}>› {prompt}</div>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${(progress * 100).toFixed(1)}%` }} />
      </div>
      <div className={styles.genFootnote}>
        reading the brief · sketching {count} tracks · matching moods · drafting per-track musicgen prompts
      </div>
    </div>
  );
}

// ============================================================================
// plan view (step 2)
// ============================================================================
type PlanViewProps = {
  prompt: string;
  plan: Track[];
  openId: string | null;
  setOpenId: (id: string | null) => void;
  onUpdate: (id: string, patch: Partial<Track>) => void;
  onRemove: (id: string) => void;
  onDuplicate: (id: string) => void;
  onAdd: () => void;
  onBack: () => void;
  onRedraft: () => void;
  onGenerate: () => void;
  totalSec: number;
  estZipMb: string;
  estGenTime: string;
};

function PlanView(p: PlanViewProps) {
  return (
    <div className={styles.fadeIn}>
      <div className={styles.planHead}>
        <div>
          <div className={styles.planEyebrow}>step 2 · review the plan</div>
          <h2 className={styles.planTitle}>Here&apos;s what the deck wants to make.</h2>
          <p className={styles.planSub}>
            Edit anything. Tweak names, descriptions, mood, length, instruments. Add tracks (max 10) or
            remove ones you don&apos;t need. When you&apos;re happy, generate.
          </p>
        </div>
        <div className={styles.planHeadRight}>
          <button className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`} type="button" onClick={p.onBack}>
            ← back
          </button>
          <button className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`} type="button" onClick={p.onRedraft}>
            redraft from prompt
          </button>
        </div>
      </div>
      <div className={styles.planSummary}>
        <strong>brief</strong> &nbsp; {p.prompt}
      </div>
      <div className={styles.planList}>
        {p.plan.map((t, i) => (
          <PlanItem
            key={t.id}
            t={t}
            i={i}
            open={p.openId === t.id}
            onToggle={() => p.setOpenId(p.openId === t.id ? null : t.id)}
            onUpdate={(patch) => p.onUpdate(t.id, patch)}
            onRemove={() => p.onRemove(t.id)}
            onDuplicate={() => p.onDuplicate(t.id)}
          />
        ))}
      </div>
      <button
        className={styles.planAdd}
        type="button"
        onClick={p.onAdd}
        disabled={p.plan.length >= MAX_TRACKS}
      >
        <span>+ add a track</span>
        <span>{p.plan.length} / {MAX_TRACKS}</span>
      </button>
      <div className={styles.planFoot}>
        <div className={styles.statRow}>
          <span><strong>{p.plan.length}</strong> · tracks planned</span>
          <span><strong>{p.totalSec}s</strong> · total length</span>
          <span><strong>~{p.estZipMb} mb</strong> · zip estimate</span>
          <span><strong>~{p.estGenTime}</strong> · est. generation</span>
        </div>
        <button
          className={`${styles.btn} ${styles.btnPrimary}`}
          type="button"
          onClick={p.onGenerate}
          disabled={p.plan.length === 0}
        >
          <span>generate audio &nbsp;→</span>
        </button>
      </div>
    </div>
  );
}

function PlanItem({
  t, i, open, onToggle, onUpdate, onRemove, onDuplicate,
}: {
  t: Track;
  i: number;
  open: boolean;
  onToggle: () => void;
  onUpdate: (patch: Partial<Track>) => void;
  onRemove: () => void;
  onDuplicate: () => void;
}) {
  return (
    <div className={`${styles.planItem} ${open ? styles.planItemOpen : ""}`}>
      <div
        className={styles.planRow}
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
      >
        <div className={styles.planIdx}>{String(i + 1).padStart(2, "0")}</div>
        <div className={styles.planBody}>
          <div className={styles.planNameRow}>
            <span className={styles.planName}>{t.name}</span>
            <span className={styles.planType}>{t.type}</span>
          </div>
          <div className={styles.planDesc}>{t.desc}</div>
        </div>
        <div className={styles.planTags}>
          <span className={styles.planTag}>{t.mood}</span>
          <span className={styles.planTag}>{t.length}s</span>
          <div className={styles.rowActions} onClick={(e) => e.stopPropagation()}>
            <button
              className={styles.rowMiniBtn}
              type="button"
              title="duplicate"
              aria-label="duplicate"
              onClick={onDuplicate}
            >
              <svg viewBox="0 0 16 16">
                <rect x="3" y="3" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4" fill="none" />
                <rect x="6" y="6" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4" fill="var(--brand-paper-lifted)" />
              </svg>
            </button>
            <button
              className={styles.rowMiniBtn}
              type="button"
              title="remove"
              aria-label="remove"
              onClick={onRemove}
            >
              <svg viewBox="0 0 16 16">
                <path d="M4 4 L12 12 M12 4 L4 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
            </button>
            <span className={styles.chev} aria-hidden="true">⌃</span>
          </div>
        </div>
      </div>
      {open && <PlanEditor t={t} onUpdate={onUpdate} />}
    </div>
  );
}

function PlanEditor({ t, onUpdate }: { t: Track; onUpdate: (patch: Partial<Track>) => void }) {
  // UX audit M6: link visible labels to their inputs via htmlFor/id so
  // clicking the label focuses the input + screen readers announce the
  // field name. The track's stable `id` makes the dom ids unique per row.
  const fid = (k: string) => `track-${t.id}-${k}`;
  return (
    <div className={styles.planEditor}>
      <div className={styles.editorGrid}>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label htmlFor={fid('name')} className={styles.fieldLab}>name</label>
          <input id={fid('name')} type="text" value={t.name} onChange={(e) => onUpdate({ name: e.target.value })} />
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label htmlFor={fid('desc')} className={styles.fieldLab}>description &amp; usage</label>
          <textarea id={fid('desc')} value={t.desc} onChange={(e) => onUpdate({ desc: e.target.value })} />
        </div>
        <div className={styles.field}>
          <label htmlFor={fid('type')} className={styles.fieldLab}>type</label>
          <select id={fid('type')} value={t.type} onChange={(e) => onUpdate({ type: e.target.value })}>
            {TYPE_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div className={styles.field}>
          <label htmlFor={fid('mood')} className={styles.fieldLab}>mood</label>
          <select id={fid('mood')} value={t.mood} onChange={(e) => onUpdate({ mood: e.target.value })}>
            {MOOD_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLab}>length</label>
          <div className={styles.seg}>
            {LENGTH_OPTIONS.map((v) => (
              <button
                key={v}
                type="button"
                className={t.length === v ? styles.segOn : ""}
                onClick={() => onUpdate({ length: v })}
              >
                {v < 60 ? `${v}s` : `${v / 60}m`}
              </button>
            ))}
          </div>
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLab}>tempo</label>
          <div className={styles.seg}>
            {TEMPO_OPTIONS.map((v) => (
              <button
                key={v}
                type="button"
                className={t.tempo === v ? styles.segOn : ""}
                onClick={() => onUpdate({ tempo: v })}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label htmlFor={fid('instruments')} className={styles.fieldLab}>instruments</label>
          <input
            id={fid('instruments')}
            type="text"
            value={t.instruments}
            onChange={(e) => onUpdate({ instruments: e.target.value })}
            placeholder="soft pads, gentle bell, no percussion"
          />
        </div>
      </div>
      <div className={styles.editorFoot}>
        <div className={styles.musicgenPreview}>
          <span className={styles.musicgenPref}>musicgen prompt &nbsp;›</span> {buildMusicgen(t)}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// generating (step 3 — real, indeterminate)
// ============================================================================
//
// We can't predict per-track progress without per-track callbacks from the
// worker (the STDB schema reports done/failed for the whole job). Rather
// than fake a progress bar that lies, we show an honest indeterminate
// indicator with the current pipeline stage ("rendering audio…",
// "unpacking tracks…") and the planned track list as a queue with no
// status — they're all queued until the zip lands.
function GeneratingView({ plan, status }: { plan: Track[]; status: string }) {
  return (
    <div className={`${styles.genCard} ${styles.fadeIn}`}>
      <div className={styles.genHead}>
        <div className={styles.genTitle}>
          {status || "starting…"}
          <span className={styles.liveBars} aria-hidden="true">
            <span /><span /><span /><span /><span />
          </span>
        </div>
        <div className={styles.genHeadRight}>
          {plan.length} {plan.length === 1 ? "track" : "tracks"}
        </div>
      </div>
      <div className={styles.genPrompt}>
        rendering each track on the deck worker — large models, slow on cpu, fast on gpu
      </div>
      <div className={styles.progressTrack}>
        <div className={`${styles.progressFill} ${styles.progressFillIndet}`} />
      </div>
      <div className={styles.genTracks}>
        {plan.map((t, i) => (
          <div key={t.id} className={styles.genTrackRow}>
            <div className={styles.genIdx}>{String(i + 1).padStart(2, "0")}</div>
            <div>
              <div className={styles.genName}>{t.name}</div>
              <div className={styles.genTrackMeta}>
                {t.type} · {t.mood} · {t.length}s
              </div>
            </div>
            <div className={styles.genMiniBar}>
              <div className={styles.genMiniFill} style={{ width: "0%" }} />
            </div>
            <div className={styles.genTime}>queued</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// error
// ============================================================================
function ErrorView({
  error, onRetry, onBack,
}: {
  error: string;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <div className={`${styles.genCard} ${styles.fadeIn}`}>
      <div className={styles.genHead}>
        <div className={styles.genTitle}>generate failed</div>
      </div>
      <div className={styles.genPrompt}>{error}</div>
      <div className={styles.editorFoot} style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <button className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`} type="button" onClick={onBack}>
          ← back to plan
        </button>
        <button className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`} type="button" onClick={onRetry}>
          retry
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// results
// ============================================================================
function Results({
  plan, estZipMb, audioByTrack, zipBlob, onEdit, onNew,
}: {
  plan: Track[];
  estZipMb: string;
  // Per-track Blob URL + filename, extracted client-side from the zip.
  // Null while the unpack is in flight or if the pipeline failed.
  audioByTrack: Map<string, TrackAudio> | null;
  // The whole zip — used to power the "download .zip" button without a
  // second network round trip.
  zipBlob: Blob | null;
  onEdit: () => void;
  onNew: () => void;
}) {
  const [zipLabel, setZipLabel] = useState("download .zip");
  const [shareLabel, setShareLabel] = useState("copy share link");
  const totalSec = plan.reduce((s, t) => s + t.length, 0);

  const onDownload = useCallback(() => {
    if (!zipBlob) {
      setZipLabel("no zip available");
      return;
    }
    triggerDownload(zipBlob, "deck.zip");
    setZipLabel("downloaded ✓");
    window.setTimeout(() => setZipLabel("download .zip"), 1400);
  }, [zipBlob]);

  return (
    <div className={styles.fadeIn}>
      <div className={styles.resultHead}>
        <div>
          <div className={styles.resultEyebrow}>step 3 · ready</div>
          <h2 className={styles.resultTitle}>
            {plan.length} {plan.length === 1 ? "track" : "tracks"} · {totalSec}s of audio
          </h2>
        </div>
        <div className={styles.resultActions}>
          <button className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`} type="button" onClick={onEdit}>
            ← edit plan
          </button>
          <button className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`} type="button" onClick={onNew}>
            new project
          </button>
          <button
            className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`}
            type="button"
            onClick={onDownload}
            disabled={!zipBlob}
          >
            <span>{zipLabel}</span>
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
              <path
                d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
      <div className={styles.tracks}>
        {plan.map((t, i) => (
          <ResultTrack
            key={t.id}
            t={t}
            i={i}
            audio={audioByTrack?.get(t.id) ?? null}
          />
        ))}
      </div>
      <div className={styles.planFoot}>
        <div className={styles.statRow}>
          <span><strong>{totalSec}s</strong> · total audio</span>
          <span><strong>44.1 khz</strong> · 16-bit wav</span>
          <span><strong>~{estZipMb} mb</strong> · zip size</span>
          <span><strong>cc-by 4.0</strong> · royalty-free</span>
        </div>
        <button
          className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`}
          type="button"
          onClick={async () => {
            const url =
              typeof window !== "undefined" ? window.location.href : "";
            if (!url) return;
            try {
              await navigator.clipboard.writeText(url);
              setShareLabel("link copied");
            } catch {
              setShareLabel("copy failed");
            }
            window.setTimeout(() => setShareLabel("copy share link"), 1400);
          }}
        >
          {shareLabel}
        </button>
      </div>
    </div>
  );
}

function ResultTrack({ t, i, audio }: { t: Track; i: number; audio: TrackAudio | null }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [duration, setDuration] = useState<number>(t.length);
  const [peaks, setPeaks] = useState<Float32Array | null>(null);

  const colorMap = ["ink", "sasta", "rust"] as const;
  const colorKey = colorMap[i % 3];
  const cssColors = { ink: "#1a1917", sasta: "#c05621", rust: "#8a3d14" };
  const color = cssColors[colorKey];

  // Decode the WAV once to extract a real waveform (peak-per-bar). Without
  // this the canvas would render an empty bar field while the <audio>
  // element handles playback. The decode also gives us the precise
  // duration, which can differ from the planned length when the renderer
  // produces a slightly different envelope.
  useEffect(() => {
    if (!audio) return;
    let cancelled = false;
    const Ctor =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    const ctx = new Ctor();
    fetch(audio.url)
      .then((r) => r.arrayBuffer())
      .then((buf) => ctx.decodeAudioData(buf))
      .then((decoded) => {
        if (cancelled) return;
        setDuration(decoded.duration);
        setPeaks(computePeaks(decoded, 200));
      })
      .catch((err) => {
        console.warn("[deck] decode failed for", audio.filename, err);
      })
      .finally(() => {
        void ctx.close();
      });
    return () => {
      cancelled = true;
    };
  }, [audio]);

  // Bind <audio> events for elapsed time + auto-stop at end.
  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setElapsed(el.currentTime);
    const onEnded = () => {
      setPlaying(false);
      setElapsed(0);
      el.currentTime = 0;
    };
    const onLoaded = () => {
      if (!Number.isNaN(el.duration) && el.duration > 0) {
        setDuration(el.duration);
      }
    };
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("ended", onEnded);
    el.addEventListener("loadedmetadata", onLoaded);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("ended", onEnded);
      el.removeEventListener("loadedmetadata", onLoaded);
    };
  }, [audio]);

  // Render the waveform canvas whenever peaks or playback position changes.
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    drawWaveform(c, peaks, color, duration > 0 ? elapsed / duration : 0);
  }, [peaks, color, elapsed, duration]);

  const togglePlay = useCallback(() => {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      void el.play().catch((err) => {
        console.warn("[deck] play failed:", err);
        setPlaying(false);
      });
      setPlaying(true);
    }
  }, [playing]);

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const el = audioRef.current;
    if (!el || duration <= 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    el.currentTime = Math.max(0, Math.min(duration, x * duration));
    if (!playing) {
      void el.play().catch(() => {/* user gesture required on some browsers */});
      setPlaying(true);
    }
  };

  const onDownloadOne = () => {
    if (!audio) return;
    triggerDownload(audio.blob, audio.filename);
  };

  const slug = slugify(t.name);
  const fmt = (s: number) => {
    const clamped = Math.max(0, Math.min(duration, s));
    const m = Math.floor(clamped / 60);
    const sec = Math.floor(clamped % 60);
    return `${m}:${String(sec).padStart(2, "0")}`;
  };
  const totalLabel = (() => {
    const d = Math.max(1, Math.round(duration));
    const m = Math.floor(d / 60);
    const sec = d % 60;
    return `${m}:${String(sec).padStart(2, "0")}`;
  })();

  const playable = !!audio;
  const filename = audio?.filename ?? `${slug}.wav`;

  return (
    <div className={`${styles.track} ${playing ? styles.trackPlaying : ""}`}>
      {audio && (
        <audio ref={audioRef} src={audio.url} preload="metadata" />
      )}
      <div className={styles.trackRow}>
        <button
          className={styles.playBtn}
          type="button"
          onClick={togglePlay}
          disabled={!playable}
          aria-label={playing ? `Pause ${t.name}` : `Play ${t.name}`}
        >
          {playing ? (
            <svg viewBox="0 0 16 16">
              <rect x="4" y="3" width="3" height="10" fill="currentColor" />
              <rect x="9" y="3" width="3" height="10" fill="currentColor" />
            </svg>
          ) : (
            <svg viewBox="0 0 16 16">
              <path d="M4 3 L13 8 L4 13 Z" fill="currentColor" />
            </svg>
          )}
        </button>
        <div className={styles.trackInfo}>
          <div className={styles.trackName}>
            {t.name} <span className={styles.filename}>{filename}</span>
          </div>
          <div className={styles.trackDesc}>
            {t.type} · {t.mood} · {t.tempo} · {t.length}s
          </div>
        </div>
        <div className={styles.trackActions}>
          <button
            className={styles.iconBtn}
            type="button"
            title="download wav"
            aria-label="Download wav"
            onClick={onDownloadOne}
            disabled={!playable}
          >
            <svg viewBox="0 0 16 16">
              <path
                d="M8 2 L8 11 M4 7 L8 11 L12 7 M3 13 L13 13"
                stroke="currentColor"
                strokeWidth="1.4"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
      <div className={styles.waveRow}>
        <canvas ref={canvasRef} className={styles.waveCanvas} width={800} height={48} onClick={onCanvasClick} />
        <div className={styles.waveTime}>
          {fmt(elapsed)} / {totalLabel}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// helpers — plan drafting (placeholder for ollama)
// ============================================================================
function nextId() {
  return `t${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

function blankTrack(): Track {
  return {
    id: nextId(),
    name: "New track",
    type: "loop",
    length: 15,
    desc: "describe what this is for",
    tempo: "90bpm",
    instruments: "pad, pluck",
    mood: "focused",
  };
}

function buildMusicgen(t: Track) {
  return `${t.mood}, ${t.type}, ${t.tempo}, ${t.length}s, ${t.instruments || "pad"} — for ${t.desc || "a project"}`;
}

type Seed = [name: string, type: string, length: number, desc: string, tempo: string, instruments: string];

function draftPlan(p: string, n: number): Track[] {
  const lower = p.toLowerCase();
  const isMeditation = /\b(meditation|mindful|sleep|calm|relax|yoga)\b/.test(lower);
  const isGame = /\b(game|platformer|rpg|puzzle|level|boss|pixel|2d|3d)\b/.test(lower);
  const isVideo = /\b(video|trailer|ad|spot|commercial|product|demo)\b/.test(lower);
  const isPodcast = /\b(podcast|intro|outro|episode|host)\b/.test(lower);
  const isFinance = /\b(finance|fintech|dashboard|analytics|trading|wealth)\b/.test(lower);
  const isApp =
    /\b(app|mobile|web|onboarding|notification|button|ui)\b/.test(lower) || isMeditation;

  let mood = "focused";
  if (isMeditation) mood = "calm";
  else if (isGame) mood = "playful";
  else if (isVideo) mood = "cinematic";
  else if (isPodcast) mood = "warm";
  else if (isFinance) mood = "focused";
  // Stem-prefix matches (no trailing \b) so "haunted", "nostalgic",
  // "energetic", "dreamy" all trigger their overrides.
  if (/\b(dark|tense|haunt|spook|grim)/.test(lower)) mood = "dark";
  if (/\b(warm|nostalg|cozy|gentle)/.test(lower)) mood = "warm";
  if (/\b(upbeat|energ|fast|hype)/.test(lower)) mood = "upbeat";
  if (/\b(dream|float|airy)/.test(lower)) mood = "dreamy";

  let candidates: Seed[] = [];
  if (isApp || isMeditation || isFinance) {
    candidates = [
      ["Background ambient bed", "background", 60, "long-form ambient bed for the home/landing screen", "60bpm", "soft pads, sustained synths, no percussion"],
      ["UI background loop", "loop", 12, "looping low-volume motif behind core flows", "90bpm", "gentle plucks, soft bells, very light rhythm"],
      ["Notification chime", "one-shot", 2, "in-app notification — friendly, non-intrusive", "free", "two-note bell, soft mallet, quick decay"],
      ["Success confirmation", "one-shot", 2, "completed action / saved / sent", "free", "rising tone, light harmonic, gentle"],
      ["Error tone", "one-shot", 2, "something went wrong — soft, not alarming", "free", "low fall, muted pad"],
      ["Onboarding intro", "intro", 8, "plays once on first open, sets the tone", "60bpm", "rising pad, single melodic phrase"],
      ["Screen transition", "transition", 3, "short whoosh between major sections", "free", "air sweep, shimmer"],
      ["Loading loop", "loop", 8, "plays during longer waits", "90bpm", "gentle pulse, soft warble"],
      ["Achievement sting", "sting", 3, "milestone celebration", "free", "bright chord stab, rising"],
      ["Outro / closing", "outro", 6, "plays as the user finishes a session", "60bpm", "descending pad, soft resolution"],
    ];
  } else if (isGame) {
    candidates = [
      ["Title theme", "intro", 30, "plays on the main menu — sets the world", "90bpm", "lead synth, drums, atmosphere"],
      ["Exploration loop", "background", 60, "core gameplay bed", "90bpm", "bass, light percussion, melodic motif"],
      ["Combat loop", "background", 30, "fight / encounter music", "120bpm", "driving drums, distorted bass, brass stabs"],
      ["Boss theme", "background", 60, "boss encounter — bigger, heavier", "120bpm", "orchestral hits, choir, percussion"],
      ["Victory sting", "sting", 3, "plays after winning a fight", "free", "rising orchestral chord, bell"],
      ["Defeat sting", "sting", 3, "plays on game-over", "free", "descending minor chord, low brass"],
      ["Menu loop", "loop", 15, "plays in pause/inventory menus", "60bpm", "soft pad, music box"],
      ["Item pickup", "one-shot", 2, "collected coin / gem / item", "free", "sparkle, bell"],
      ["Hit / damage", "one-shot", 2, "enemy or player takes damage", "free", "punchy thud"],
      ["Level complete", "sting", 4, "end of stage celebration", "free", "fanfare, drums"],
    ];
  } else if (isPodcast) {
    candidates = [
      ["Intro theme", "intro", 15, "opening signature for every episode", "90bpm", "acoustic guitar, soft kick, atmosphere"],
      ["Outro theme", "outro", 15, "closing signature", "90bpm", "acoustic guitar, light strings"],
      ["Ad break bumper", "transition", 5, "bumper between content and sponsor read", "free", "short tag, branded"],
      ["Interview bed", "background", 30, "subtle bed under longer interview segments", "60bpm", "soft pad, no melody"],
      ["Pull-quote sting", "sting", 3, "highlights a guest soundbite", "free", "small chord, pluck"],
      ["Episode-end card", "outro", 8, "plays under credits / patreon mentions", "60bpm", "warm pad, light arpeggio"],
    ];
  } else if (isVideo) {
    candidates = [
      ["Hero music bed", "background", 30, "main backing track for the spot", "90bpm", "cinematic pad, light percussion, melody"],
      ["Opening sting", "intro", 4, "plays under the logo / first frame", "free", "rising chord, percussive hit"],
      ["Closing sting", "outro", 4, "plays under the end card / CTA", "free", "resolving chord, gentle hit"],
      ["Tagline bumper", "transition", 3, "punctuates the tagline reveal", "free", "snap, shimmer"],
      ["Voiceover bed", "background", 30, "subtle, no melody under VO", "60bpm", "pad, sub bass"],
    ];
  } else {
    candidates = [
      ["Background bed", "background", 30, "main long-form audio bed", "90bpm", "pad, soft melody"],
      ["Short loop", "loop", 12, "compact looping motif", "90bpm", "pluck, soft drums"],
      ["Notification tone", "one-shot", 2, "short signal / chime", "free", "bell, mallet"],
      ["Intro sting", "intro", 4, "opening hit", "free", "rising chord"],
      ["Outro sting", "outro", 4, "closing hit", "free", "resolving chord"],
    ];
  }

  const out: Track[] = candidates.slice(0, n).map((c) => ({
    id: nextId(),
    name: c[0],
    type: c[1],
    length: c[2],
    desc: c[3],
    tempo: c[4],
    instruments: c[5],
    mood,
  }));
  while (out.length < n) {
    out.push({
      id: nextId(),
      name: `Extra track ${out.length + 1}`,
      type: "loop",
      length: 15,
      desc: "additional looping motif",
      tempo: "90bpm",
      instruments: "pad, pluck",
      mood,
    });
  }
  return out;
}

// ============================================================================
// helpers — real PCM waveform + zip unpack
// ============================================================================

// Reduce a decoded AudioBuffer to ``bars`` peak amplitudes — one number in
// [0, 1] per output bar, taken as the max abs sample over the slice.
// Mixes channels by averaging so a stereo source still renders as one bar
// strip.
function computePeaks(buffer: AudioBuffer, bars: number): Float32Array {
  const out = new Float32Array(bars);
  const samples = buffer.length;
  if (samples === 0) return out;
  const channels = buffer.numberOfChannels;
  const data: Float32Array[] = [];
  for (let c = 0; c < channels; c++) data.push(buffer.getChannelData(c));
  const step = samples / bars;
  for (let i = 0; i < bars; i++) {
    const start = Math.floor(i * step);
    const end = Math.min(samples, Math.floor((i + 1) * step));
    let peak = 0;
    for (let s = start; s < end; s++) {
      let v = 0;
      for (let c = 0; c < channels; c++) v += data[c][s];
      v = Math.abs(v / channels);
      if (v > peak) peak = v;
    }
    out[i] = peak;
  }
  // Normalize to the clip's loudest peak so quiet tracks still render
  // visible bars.
  let max = 0;
  for (let i = 0; i < bars; i++) if (out[i] > max) max = out[i];
  if (max > 0) {
    for (let i = 0; i < bars; i++) out[i] = out[i] / max;
  }
  return out;
}

function drawWaveform(
  canvas: HTMLCanvasElement,
  peaks: Float32Array | null,
  color: string,
  progress: number,
) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 800;
  const cssH = 48;
  if (canvas.width !== cssW * dpr) {
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  const barW = 2;
  const gap = 2;
  const total = Math.floor(cssW / (barW + gap));
  const playedTo = Math.floor(progress * total);
  for (let i = 0; i < total; i++) {
    const peak = peaks ? peaks[Math.floor((i / total) * peaks.length)] ?? 0 : 0;
    const h = Math.max(2, peak * (cssH - 4));
    const x = i * (barW + gap);
    const y = (cssH - h) / 2;
    ctx.fillStyle = i <= playedTo ? color : "rgba(168,161,150,0.55)";
    ctx.fillRect(x, y, barW, h);
  }
}

// Unzip the bundle and pair each WAV (sorted by leading numeric prefix —
// the worker writes them as `01-name.wav`, `02-name.wav`…) with the plan
// track at the same index. Returns a Map keyed by track id so ResultTrack
// can look up its blob/url.
async function unpackZipToTracks(
  zip: Blob,
  plan: Track[],
): Promise<Map<string, TrackAudio>> {
  const buf = new Uint8Array(await zip.arrayBuffer());
  let entries: Record<string, Uint8Array>;
  try {
    entries = unzipSync(buf);
  } catch (err) {
    throw new Error(
      `not a valid zip — backend may be in offline/demo mode: ${String(err)}`,
    );
  }
  const wavs = Object.entries(entries)
    .filter(([name]) => name.toLowerCase().endsWith(".wav"))
    .sort(([a], [b]) => a.localeCompare(b, "en", { numeric: true }));
  if (wavs.length === 0) {
    throw new Error("zip contained no WAV files");
  }
  const map = new Map<string, TrackAudio>();
  const limit = Math.min(plan.length, wavs.length);
  for (let i = 0; i < limit; i++) {
    const [filename, bytes] = wavs[i];
    // Copy into a fresh ArrayBuffer so the Blob owns its memory and the
    // subsequent ArrayBuffer slice from `bytes` doesn't get GC'd
    // unexpectedly.
    const blob = new Blob([new Uint8Array(bytes)], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    map.set(plan[i].id, { url, filename, blob });
  }
  return map;
}

// ============================================================================
// helpers — backend API
// ============================================================================
async function fetchPlan(apiUrl: string, description: string, count: number): Promise<Track[]> {
  const r = await fetch(`${apiUrl.replace(/\/$/, "")}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, count }),
  });
  if (!r.ok) throw new Error(`plan ${r.status}`);
  const body = (await r.json()) as { tracks: ApiTrack[] };
  return body.tracks.map((t) => ({
    id: nextId(),
    name: t.name,
    type: t.type,
    length: t.length,
    desc: t.desc,
    tempo: t.tempo,
    instruments: t.instruments,
    mood: t.mood,
  }));
}

type ApiTrack = {
  name: string;
  type: string;
  length: number;
  desc: string;
  tempo: string;
  instruments: string;
  mood: string;
};

async function fetchGenerate(apiUrl: string, description: string, plan: Track[]): Promise<Blob> {
  // Drop client-side ids — the backend assigns its own filenames.
  const tracks = plan.map((t) => {
    const { id, ...rest } = t;
    void id;
    return rest;
  });
  const r = await fetch(`${apiUrl.replace(/\/$/, "")}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, count: plan.length, tracks }),
  });
  if (!r.ok) throw new Error(`generate ${r.status}`);
  return await r.blob();
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke after a tick so the browser has time to start the download stream.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slugify(s: string) {
  return (
    s
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 30) || "track"
  );
}
