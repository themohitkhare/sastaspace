"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./deck.module.css";
// Phase 2 F4 — STDB-native plan/generate path. Both this and the legacy
// HTTP path coexist behind NEXT_PUBLIC_USE_STDB_DECK; the flag picks one
// at build time. TODO(Phase 4 modularization): once cutover is stable,
// the legacy path + this flag both go away and Deck.tsx splits into
// per-step components (audit M1).
import { useDeckStdb, type DeckStdb } from "./useDeckStdb";
import {
  submitPlan,
  submitGenerate,
  downloadZipFromUrl,
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

type TrackKind = "pad" | "loop" | "ping";

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

  const reset = useCallback(() => {
    setPrompt("");
    setPlan([]);
    setOpenId(null);
    setPhase("idle");
    setPlanProgress(0);
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const onClear = useCallback(() => {
    setPrompt("");
    setPhase("idle");
    setPlan([]);
    setOpenId(null);
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
            <GeneratingView
              plan={plan}
              onDone={() => setPhase("results")}
            />
          )}
          {phase === "results" && (
            <Results
              plan={plan}
              estZipMb={estZipMb}
              prompt={trimmed}
              onEdit={() => setPhase("plan")}
              onNew={reset}
              stdb={stdb}
              stdbPlanId={stdbPlanId}
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
        <div className={styles.composerLabel}>describe what you&apos;re building</div>
        <div className={styles.composerCount}>{value.length} / 600</div>
      </div>
      <textarea
        ref={promptRef}
        value={value}
        maxLength={600}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="A meditation app for stressed professionals. Calm, slow, breathing-paced. Soft pads, no percussion."
        spellCheck={false}
      />
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
  return (
    <div className={styles.planEditor}>
      <div className={styles.editorGrid}>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className={styles.fieldLab}>name</label>
          <input type="text" value={t.name} onChange={(e) => onUpdate({ name: e.target.value })} />
        </div>
        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label className={styles.fieldLab}>description &amp; usage</label>
          <textarea value={t.desc} onChange={(e) => onUpdate({ desc: e.target.value })} />
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLab}>type</label>
          <select value={t.type} onChange={(e) => onUpdate({ type: e.target.value })}>
            {TYPE_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.fieldLab}>mood</label>
          <select value={t.mood} onChange={(e) => onUpdate({ mood: e.target.value })}>
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
          <label className={styles.fieldLab}>instruments</label>
          <input
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
// generating (step 3 — transient)
// ============================================================================
function GeneratingView({ plan, onDone }: { plan: Track[]; onDone: () => void }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);
  const [doneIdxs, setDoneIdxs] = useState<Set<number>>(new Set());

  const durs = useMemo(() => plan.map((t) => Math.max(900, t.length * 120)), [plan]);
  const total = useMemo(() => durs.reduce((a, b) => a + b, 0), [durs]);

  useEffect(() => {
    if (plan.length === 0) {
      onDone();
      return;
    }
    let idx = 0;
    let stepStart = performance.now();
    const tick = window.setInterval(() => {
      const now = performance.now();
      const inStep = now - stepStart;
      const r = Math.min(inStep / durs[idx], 1);
      setStepProgress(r);
      if (r >= 1) {
        setDoneIdxs((prev) => new Set(prev).add(idx));
        idx += 1;
        if (idx >= plan.length) {
          window.clearInterval(tick);
          window.setTimeout(onDone, 350);
          return;
        }
        stepStart = performance.now();
        setActiveIdx(idx);
        setStepProgress(0);
      }
    }, 80);
    return () => window.clearInterval(tick);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const overall = useMemo(() => {
    const before = durs.slice(0, activeIdx).reduce((a, b) => a + b, 0);
    return total === 0 ? 0 : (before + stepProgress * (durs[activeIdx] ?? 0)) / total;
  }, [activeIdx, stepProgress, durs, total]);

  return (
    <div className={`${styles.genCard} ${styles.fadeIn}`}>
      <div className={styles.genHead}>
        <div className={styles.genTitle}>
          generating {plan.length} {plan.length === 1 ? "track" : "tracks"}&hellip;
          <span className={styles.liveBars} aria-hidden="true">
            <span /><span /><span /><span /><span />
          </span>
        </div>
        <div className={styles.genHeadRight}>{Math.round(overall * 100)}%</div>
      </div>
      <div className={styles.genPrompt}>
        running each track through musicgen with its own settings &mdash; cpu, sequential
      </div>
      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${(overall * 100).toFixed(1)}%` }} />
      </div>
      <div className={styles.genTracks}>
        {plan.map((t, i) => {
          const isDone = doneIdxs.has(i);
          const isActive = i === activeIdx && !isDone;
          const fill = isDone ? 1 : isActive ? stepProgress : 0;
          const label = isDone ? "done" : isActive ? "running" : "queued";
          return (
            <div
              key={t.id}
              className={`${styles.genTrackRow} ${
                isDone ? styles.genTrackRowDone : isActive ? styles.genTrackRowActive : ""
              }`}
            >
              <div className={styles.genIdx}>{String(i + 1).padStart(2, "0")}</div>
              <div>
                <div className={styles.genName}>{t.name}</div>
                <div className={styles.genTrackMeta}>
                  {t.type} · {t.mood} · {t.length}s
                </div>
              </div>
              <div className={styles.genMiniBar}>
                <div className={styles.genMiniFill} style={{ width: `${(fill * 100).toFixed(0)}%` }} />
              </div>
              <div className={styles.genTime}>{label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// results
// ============================================================================
function Results({
  plan, estZipMb, prompt, onEdit, onNew, stdb, stdbPlanId,
}: {
  plan: Track[];
  estZipMb: string;
  prompt: string;
  onEdit: () => void;
  onNew: () => void;
  // Phase 2 F4 — present only when USE_STDB is on; otherwise null and
  // onDownload falls through to the legacy HTTP/stub path.
  stdb: DeckStdb | null;
  stdbPlanId: bigint | null;
}) {
  const [zipLabel, setZipLabel] = useState("download .zip");
  const [shareLabel, setShareLabel] = useState("copy share link");
  const totalSec = plan.reduce((s, t) => s + t.length, 0);

  const onDownload = useCallback(async () => {
    setZipLabel("building zip…");
    try {
      // ────────── F4: STDB path ──────────
      if (USE_STDB && stdb) {
        // Strip client-side ids before sending to the reducer.
        const tracks: StdbTrack[] = plan.map(({ id, ...rest }) => {
          void id;
          return rest;
        });
        const res = await submitGenerate(
          stdb.conn,
          stdb.identityHex,
          stdbPlanId,
          tracks,
        );
        if (res.kind === "done") {
          await downloadZipFromUrl(res.zipUrl, "deck.zip");
          setZipLabel("downloaded ✓");
        } else {
          console.warn("[deck] stdb generate failed:", res.error);
          setZipLabel("download failed — retry");
        }
        return;
      }
      // ────────── legacy: HTTP path ──────────
      const blob = API_URL
        ? await fetchGenerate(API_URL, prompt, plan)
        : await stubZipBlob();
      triggerDownload(blob, "deck.zip");
      setZipLabel("downloaded ✓");
    } catch (err) {
      console.warn("[deck] /generate failed:", err);
      setZipLabel("download failed — retry");
    }
  }, [plan, prompt, stdb, stdbPlanId]);

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
          <ResultTrack key={t.id} t={t} i={i} />
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

function ResultTrack({ t, i }: { t: Track; i: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [pos, setPos] = useState(0); // 0..1
  const [elapsed, setElapsed] = useState(0); // seconds
  const seed = useMemo(() => hash(t.name + t.desc + t.mood + i), [t.name, t.desc, t.mood, i]);
  const colorMap = ["ink", "sasta", "rust"] as const;
  const colorKey = colorMap[i % 3];
  const cssColors = { ink: "#1a1917", sasta: "#c05621", rust: "#8a3d14" };
  const color = cssColors[colorKey];
  const kind = pickKind(t);

  // playback state — kept in refs so re-renders don't rebuild voices
  const ctxRef = useRef<AudioContext | null>(null);
  const voiceRef = useRef<{ stop: () => void } | null>(null);
  const startedAtRef = useRef(0);
  const offsetRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  const draw = useCallback(
    (progress: number) => {
      const c = canvasRef.current;
      if (!c) return;
      drawWaveform(c, seed, color, progress);
    },
    [seed, color],
  );

  useEffect(() => {
    draw(0);
  }, [draw]);

  const stop = useCallback(() => {
    voiceRef.current?.stop();
    voiceRef.current = null;
    setPlaying(false);
    setPos(0);
    setElapsed(0);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    draw(0);
  }, [draw]);

  const play = useCallback(
    (from = 0) => {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return;
      if (!ctxRef.current) ctxRef.current = new Ctor();
      const ctx = ctxRef.current;
      if (ctx.state === "suspended") void ctx.resume();
      voiceRef.current?.stop();
      const v = synthVoice(ctx, kind, t.length, from);
      voiceRef.current = v;
      startedAtRef.current = ctx.currentTime;
      offsetRef.current = from;
      setPlaying(true);

      const tick = () => {
        const c = ctxRef.current;
        if (!c) return;
        const e = c.currentTime - startedAtRef.current + offsetRef.current;
        const p = Math.min(e / t.length, 1);
        setElapsed(e);
        setPos(p);
        draw(p);
        if (e >= t.length) {
          stop();
          return;
        }
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    },
    [kind, t.length, draw, stop],
  );

  useEffect(() => {
    return () => {
      voiceRef.current?.stop();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const target = Math.max(0, Math.min(t.length, x * t.length));
    stop();
    play(target);
  };

  const slug = slugify(t.name);
  const fmt = (s: number) => {
    const clamped = Math.max(0, Math.min(t.length, s));
    const m = Math.floor(clamped / 60);
    const sec = Math.floor(clamped % 60);
    return `${m}:${String(sec).padStart(2, "0")}`;
  };

  // suppress unused warning — `pos` powers the rerender that drives `draw`
  void pos;

  return (
    <div className={`${styles.track} ${playing ? styles.trackPlaying : ""}`}>
      <div className={styles.trackRow}>
        <button
          className={styles.playBtn}
          type="button"
          onClick={() => (playing ? stop() : play(0))}
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
            {t.name} <span className={styles.filename}>{slug}.wav</span>
          </div>
          <div className={styles.trackDesc}>
            {t.type} · {t.mood} · {t.tempo} · {t.length}s
          </div>
        </div>
        <div className={styles.trackActions}>
          <button className={styles.iconBtn} type="button" title="regenerate" aria-label="Regenerate">
            <svg viewBox="0 0 16 16">
              <path
                d="M3 8 a5 5 0 0 1 9 -3 M12 3 L12 6 L9 6 M13 8 a5 5 0 0 1 -9 3 M4 13 L4 10 L7 10"
                stroke="currentColor"
                strokeWidth="1.4"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <button className={styles.iconBtn} type="button" title="download wav" aria-label="Download">
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
          {fmt(elapsed)} / 0:{String(t.length).padStart(2, "0")}
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

function pickKind(t: Track): TrackKind {
  if (t.type === "one-shot" || t.length <= 4 || /notify|notification|sting|alert/i.test(t.name + t.type)) {
    return "ping";
  }
  if (t.type === "loop" || /loop|ui|button/i.test(t.name + t.type)) return "loop";
  return "pad";
}

// ============================================================================
// helpers — waveform + audio
// ============================================================================
function drawWaveform(canvas: HTMLCanvasElement, seed: number, color: string, progress: number) {
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
  const rng = mulberry32(seed);
  const playedTo = Math.floor(progress * total);
  for (let i = 0; i < total; i++) {
    const r = rng();
    const t = i / total;
    const env = 0.35 + 0.65 * Math.sin(Math.PI * t);
    const h = Math.max(2, (r * 0.85 + 0.15) * env * (cssH - 4));
    const x = i * (barW + gap);
    const y = (cssH - h) / 2;
    ctx.fillStyle = i <= playedTo ? color : "rgba(168,161,150,0.55)";
    ctx.fillRect(x, y, barW, h);
  }
}

function mulberry32(a: number) {
  let s = a;
  return function () {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function synthVoice(ctx: AudioContext, kind: TrackKind, length: number, from = 0) {
  const gain = ctx.createGain();
  gain.gain.value = 0;
  gain.connect(ctx.destination);
  let stopFn: () => void;

  if (kind === "pad") {
    const m = ctx.createGain();
    m.gain.value = 0.15;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 900;
    [220, 277.18, 329.63].forEach((f, i) => {
      const o = ctx.createOscillator();
      o.type = i === 1 ? "triangle" : "sine";
      o.frequency.value = f * (1 + (i - 1) * 0.005);
      const lfo = ctx.createOscillator();
      lfo.frequency.value = 0.12 + i * 0.04;
      const lg = ctx.createGain();
      lg.gain.value = 1.5;
      lfo.connect(lg).connect(o.detune);
      o.connect(m);
      o.start();
      lfo.start();
    });
    m.connect(lp).connect(gain);
    gain.gain.linearRampToValueAtTime(0.25, ctx.currentTime + 0.6);
    stopFn = () => {
      gain.gain.cancelScheduledValues(ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.05);
    };
  } else if (kind === "loop") {
    const m = ctx.createGain();
    m.gain.value = 0.18;
    m.connect(gain);
    const notes = [392, 466, 523, 587];
    const beat = 0.5;
    const endT = ctx.currentTime + (length - from);
    let beatI = Math.floor(from / beat);
    let timer: number;
    const plink = () => {
      const now = ctx.currentTime;
      if (now >= endT) return;
      const f = notes[beatI % notes.length] * (beatI % 8 === 7 ? 0.5 : 1);
      const o = ctx.createOscillator();
      o.type = "triangle";
      o.frequency.value = f;
      const g = ctx.createGain();
      g.gain.value = 0;
      o.connect(g).connect(m);
      g.gain.linearRampToValueAtTime(0.5, now + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      o.start(now);
      o.stop(now + 0.45);
      beatI++;
      timer = window.setTimeout(plink, beat * 1000);
    };
    timer = window.setTimeout(plink, 0);
    gain.gain.linearRampToValueAtTime(1, ctx.currentTime + 0.1);
    stopFn = () => {
      window.clearTimeout(timer);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.05);
    };
  } else {
    const o1 = ctx.createOscillator();
    o1.type = "sine";
    o1.frequency.value = 880;
    const o2 = ctx.createOscillator();
    o2.type = "sine";
    o2.frequency.value = 1318.5;
    const g1 = ctx.createGain();
    const g2 = ctx.createGain();
    g1.gain.value = 0;
    g2.gain.value = 0;
    o1.connect(g1).connect(gain);
    o2.connect(g2).connect(gain);
    const t0 = ctx.currentTime;
    g1.gain.linearRampToValueAtTime(0.3, t0 + 0.02);
    g1.gain.exponentialRampToValueAtTime(0.001, t0 + 0.5);
    g2.gain.linearRampToValueAtTime(0.25, t0 + 0.18);
    g2.gain.exponentialRampToValueAtTime(0.001, t0 + 1.0);
    o1.start(t0);
    o2.start(t0 + 0.15);
    o1.stop(t0 + 0.6);
    o2.stop(t0 + 1.1);
    gain.gain.value = 1;
    stopFn = () => {
      try { o1.stop(); } catch { /* already stopped */ }
      try { o2.stop(); } catch { /* already stopped */ }
    };
  }

  return { stop: stopFn };
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

async function stubZipBlob(): Promise<Blob> {
  // Offline mode — empty placeholder so the download UI flow still completes
  // for demos. The real round-trip is exercised when NEXT_PUBLIC_DECK_API_URL
  // is set against a running deck service.
  return new Blob(
    [
      "deck — sastaspace audio designer\n" +
        "================================\n\n" +
        "offline mode — set NEXT_PUBLIC_DECK_API_URL to fetch real WAVs.\n",
    ],
    { type: "text/plain" },
  );
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

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
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
