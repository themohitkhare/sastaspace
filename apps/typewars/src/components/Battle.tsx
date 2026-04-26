'use client';
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSpacetimeDB, useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/typewars-bindings';
import type { Player, Region, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  player: Player;
  region: Region;       // snapshot at battle entry; subscription provides live updates
  onExit: () => void;
}

export default function Battle({ player, region, onExit }: Props) {
  const { identity } = useSpacetimeDB();

  // --- Subscriptions ---
  // Subscribe to all active sessions for this player, filter active client-side
  // (avoids .and() chaining which hits a dual-module BooleanExpr type mismatch)
  const sessionQuery = useMemo(
    () => identity
      ? tables.battle_session.where(s => s.playerIdentity.eq(identity))
      : tables.battle_session.where(() => false),
    [identity],
  );
  const [sessionRows] = useTable(sessionQuery);
  const session = sessionRows.find(s => s.active); // at most one active session per player

  // Keep a stable session id so wordQuery doesn't flip to false mid-battle
  const activeSessionId = session?.id;

  const wordQuery = useMemo(
    () => activeSessionId !== undefined
      ? tables.word.where(w => w.sessionId.eq(activeSessionId))
      : tables.word.where(() => false),
    [activeSessionId],
  );
  const [serverWords] = useTable(wordQuery);

  const regionQuery = useMemo(
    () => tables.region.where(r => r.id.eq(region.id)),
    [region.id],
  );
  const [regionRows] = useTable(regionQuery);
  // fall back to prop until subscription lands; regionRows come back with bigint fields
  const liveRegionRow = regionRows[0];

  // --- Reducers ---
  const startBattle = useReducer(reducers.startBattle);
  const submitWordReducer = useReducer(reducers.submitWord);
  const endBattle = useReducer(reducers.endBattle);

  // --- Lifecycle: start once ---
  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    if (session) return; // don't double-start if a session already exists
    startedRef.current = true;
    startBattle({ regionId: region.id }).catch(err => console.error('start_battle', err));
  }, [session, region.id, startBattle]);

  // --- Lifecycle: end on unmount ---
  const sessionIdRef = useRef<bigint | undefined>(undefined);
  const sessionId = session?.id;
  useEffect(() => {
    if (sessionId !== undefined) sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    return () => {
      const sid = sessionIdRef.current;
      if (sid !== undefined) {
        endBattle({ sessionId: sid }).catch(() => { /* noop on unmount */ });
      }
    };
    // endBattle is stable; only run on unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Client state ---
  const [input, setInput] = useState('');

  // --- WPM tick: startMs comes from server (session.startedAt), now ticks via interval ---
  const [now, setNow] = useState<number>(0);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  // --- Visuals from session diff ---
  const prevStreakRef = useRef(0);
  const [ashFlash, setAshFlash] = useState(false);
  const [shaking, setShaking] = useState(false);

  const sessionStreak = session?.streak;
  useEffect(() => {
    if (sessionStreak === undefined) return;
    const prev = prevStreakRef.current;
    const cur = sessionStreak;
    if (cur === 0 && prev > 0) {
      setShaking(true);
      setTimeout(() => setShaking(false), 300);
    }
    if (player.legion === 0 && cur === 0 && prev > 0 && prev % 10 === 0) {
      setAshFlash(true);
      setTimeout(() => setAshFlash(false), 400);
    }
    prevStreakRef.current = cur;
  }, [sessionStreak, player.legion]);

  // --- Submit on Enter or Space ---
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    e.preventDefault();
    const typed = input.trim().toLowerCase();
    if (!typed || !session) return;
    setInput('');
    submitWordReducer({ sessionId: session.id, word: typed }).catch(() => { /* server errors silently */ });
  }, [input, session, submitWordReducer]);

  // --- Loading state ---
  if (!session) {
    return (
      <div className="battle-screen" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="ss-terminal">engaging {region.name}…</span>
      </div>
    );
  }

  // --- Derived display values ---
  const legion = LEGION_INFO[player.legion];
  const multCap = player.legion === 3 ? 5.0 : 3.0;
  const isOverdrive = player.legion === 3 && session.multiplier >= 3.0;

  const startMs = session?.startedAt ? Number(session.startedAt.toMillis()) : 0;
  const elapsedMin = startMs > 0 && now > 0 ? Math.max(0, (now - startMs) / 60000) : 0;
  const hits = session.accuracyHits;
  const misses = session.accuracyMisses;
  const wpm = elapsedMin > 0 ? Math.round(hits / elapsedMin) : 0;
  const acc = hits + misses > 0 ? Math.round((hits / (hits + misses)) * 100) : 100;

  // Region HP — use live subscription row if available, else fall back to prop
  const enemyHp = liveRegionRow ? Number(liveRegionRow.enemyHp) : region.enemy_hp;
  const enemyMaxHp = liveRegionRow ? Number(liveRegionRow.enemyMaxHp) : region.enemy_max_hp;
  const hpPct = enemyMaxHp > 0 ? (enemyHp / enemyMaxHp) * 100 : 0;

  // Contribution bar — bigint fields on liveRegionRow
  const d0 = liveRegionRow ? Number(liveRegionRow.damage0) : region.damage_0;
  const d1 = liveRegionRow ? Number(liveRegionRow.damage1) : region.damage_1;
  const d2 = liveRegionRow ? Number(liveRegionRow.damage2) : region.damage_2;
  const d3 = liveRegionRow ? Number(liveRegionRow.damage3) : region.damage_3;
  const d4 = liveRegionRow ? Number(liveRegionRow.damage4) : region.damage_4;
  const damages = [d0, d1, d2, d3, d4];
  const totalContrib = d0 + d1 + d2 + d3 + d4;

  const damageDealt = Number(session.damageDealt ?? 0n);

  // Words from server — sort by id ascending, render up to 8
  const sortedWords = [...serverWords].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const displayWords = sortedWords.slice(0, 8);

  // Match input prefix to a word for live typing feedback
  const matchingWord = input.length > 0
    ? displayWords.find(w => w.text.startsWith(input.toLowerCase()))
    : null;

  return (
    <div className="battle-screen" style={{ ['--legion-color' as string]: legion.color }}>
      {/* Header */}
      <div className="battle-header">
        <div className="battle-header-left">
          <button className="back-btn" onClick={onExit}>← exit</button>
          <span className="ss-label" style={{ color: 'var(--brand-muted)' }}>
            {region.name} · T{region.tier}
          </span>
        </div>
        <div className="battle-header-right">
          <div className="hud-stat">
            <span className="hud-label">WPM</span>
            <span className="hud-val">{wpm}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">ACC</span>
            <span className="hud-val">{acc}%</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">DMG</span>
            <span className="hud-val">{damageDealt.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Region HP */}
      <div className="region-hp-wrap">
        <div className="region-hp-meta">
          <div>
            <p className="ss-label" style={{ color: 'var(--brand-muted)', marginBottom: 4 }}>{region.name}</p>
            <div className="hp-numbers">
              <span className="hp-current">{enemyHp.toLocaleString()}</span>
              <span className="hp-sep">/</span>
              <span className="hp-max">{enemyMaxHp.toLocaleString()}</span>
            </div>
          </div>
          <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>
            {region.active_wardens} wardens
          </span>
        </div>
        <div className="hp-bar-outer">
          <div className="hp-bar-inner" style={{ width: `${hpPct}%` }} />
        </div>

        {/* Contribution bar */}
        <div className="contrib-bar">
          {([0, 1, 2, 3, 4] as LegionId[]).map(id => {
            const dmg = damages[id];
            const pct = totalContrib > 0 ? (dmg / totalContrib) * 100 : 0;
            if (pct === 0) return null;
            const info = LEGION_INFO[id];
            return (
              <div key={id} className="contrib-seg" style={{ width: `${pct}%`, background: info.color }}>
                {pct > 8 && <span className="contrib-lbl">{info.short}</span>}
              </div>
            );
          })}
        </div>
        <div className="contrib-legend">
          {([0, 1, 2, 3, 4] as LegionId[]).map(id => {
            const dmg = damages[id];
            if (dmg === 0) return null;
            const info = LEGION_INFO[id];
            return (
              <div key={id} className="contrib-leg-item">
                <div className="contrib-dot" style={{ background: info.color }} />
                <span className="ss-small">{info.name}</span>
                <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>{dmg.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Word grid */}
      <div className={`words-grid${ashFlash ? ' ash-flash' : ''}`}>
        {displayWords.map(w => {
          const expiresMs = Number(w.expiresAt.toMillis());
          const lifeLeft = Math.max(0, expiresMs - now);
          const lifePct = (lifeLeft / 5000) * 100;
          const isMatching = matchingWord?.id === w.id;
          const isUrgent = lifeLeft < 1500;
          const typed = isMatching ? input.toLowerCase() : '';
          const rest = isMatching ? w.text.slice(typed.length) : w.text;

          return (
            <div
              key={String(w.id)}
              className={[
                'word-card',
                `diff-${w.difficulty}`,
                isMatching ? 'matching' : '',
                isUrgent ? 'urgent' : '',
              ].filter(Boolean).join(' ')}
            >
              <div>
                <div className="word-meta">
                  {player.legion === 4 ? (
                    <span className="word-diff">d{w.difficulty}</span>
                  ) : (
                    <span className="word-diff">·</span>
                  )}
                  <span className="word-dmg">{Number(w.baseDamage)}dmg</span>
                </div>
                <div className="word-text">
                  {isMatching ? (
                    <>
                      <span className="word-typed">{typed}</span>
                      <span className="word-rest">{rest}</span>
                    </>
                  ) : (
                    <span className="word-rest">{w.text}</span>
                  )}
                </div>
              </div>
              <div className="word-life-outer">
                <div
                  className="word-life-inner"
                  style={{
                    width: `${lifePct}%`,
                    background: isUrgent ? 'var(--brand-sasta)' : 'var(--brand-ink)',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Input row */}
      <div className={`battle-input-row${shaking ? ' shake' : ''}`}>
        <div className="streak-card">
          <span className="streak-label">streak</span>
          <span className="streak-num">{session.streak}</span>
        </div>
        <div className="input-wrap">
          <span className="prompt">›</span>
          <input
            className="battle-input"
            autoFocus
            placeholder="type a word…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
          />
        </div>
        <div className={`mult-card${isOverdrive ? ' overdrive' : ''}`}>
          <span className="streak-label">mult</span>
          <span className="streak-num">{session.multiplier.toFixed(2)}×</span>
          <span className="mult-cap">cap {multCap.toFixed(1)}×</span>
        </div>
      </div>

      {/* Legion HUD */}
      <div className="legion-hud">
        <span className="legion-badge" style={{ color: legion.color, borderColor: legion.color }}>
          {legion.short} · {legion.mechanic}
        </span>
        <span className="ss-small legion-hint">{legion.text}</span>
      </div>
    </div>
  );
}
