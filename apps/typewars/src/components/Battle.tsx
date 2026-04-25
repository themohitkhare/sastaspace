'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { Player, Region, LegionId, WordState } from '@/types';
import { LEGION_INFO } from '@/lib/legions';
import { makeWord } from '@/lib/words';

interface Props {
  player: Player;
  region: Region;
  onExit: () => void;
  dispatchDamage: (regionId: number, legion: LegionId, amount: number) => void;
}

const INITIAL_DIST = [1, 1, 1, 1, 1, 2, 2, 3];

function initWords(t: number): WordState[] {
  return INITIAL_DIST.map((diff, i) => makeWord(i, t, diff));
}

export default function Battle({ player, region, onExit, dispatchDamage }: Props) {
  const nowRef = useRef<number>(Date.now());
  const [now, setNow] = useState<number>(Date.now());
  const [words, setWords] = useState<WordState[]>(() => initWords(Date.now()));
  const [input, setInput] = useState('');
  const [streak, setStreak] = useState(0);
  const [multiplier, setMultiplier] = useState(1);
  const [totalDmg, setTotalDmg] = useState(0);
  const [totalWords, setTotalWords] = useState(0);
  const [totalMisses, setTotalMisses] = useState(0);
  const [startTime] = useState(Date.now());
  const [hitId, setHitId] = useState<number | null>(null);
  const [ashFlash, setAshFlash] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [regionHp, setRegionHp] = useState(region.enemy_hp);
  const [myDamage, setMyDamage] = useState(0);
  const idCounter = useRef(INITIAL_DIST.length);

  const legion = LEGION_INFO[player.legion];
  const multCap = player.legion === 3 ? 5.0 : 3.0;
  const isOverdrive = player.legion === 3 && multiplier >= 3.0;

  // 80ms tick for now
  useEffect(() => {
    const id = setInterval(() => {
      const t = Date.now();
      nowRef.current = t;
      setNow(t);
    }, 80);
    return () => clearInterval(id);
  }, []);

  // Expire check
  useEffect(() => {
    const expired = words.filter(w => now >= w.expires_at);
    if (expired.length === 0) return;
    setStreak(0);
    setMultiplier(1);
    const t = nowRef.current;
    setWords(prev => {
      const surviving = prev.filter(w => now < w.expires_at);
      const needed = 8 - surviving.length;
      const newWords: WordState[] = [];
      for (let i = 0; i < needed; i++) {
        newWords.push(makeWord(idCounter.current++, t));
      }
      return [...surviving, ...newWords];
    });
  }, [now, words]);

  const submitWord = useCallback(() => {
    const typed = input.trim().toLowerCase();
    if (!typed) return;

    const matchIdx = words.findIndex(w => w.text === typed);
    if (matchIdx !== -1) {
      const w = words[matchIdx];
      const newStreak = streak + 1;
      const newMult = Math.min(multCap, 1 + newStreak * 0.25);
      const newTotalWords = totalWords + 1;

      let dmg = Math.round(w.base_damage * newMult);

      // Ashborn burst at streak % 10 === 0
      let doAshFlash = false;
      if (player.legion === 0 && newStreak % 10 === 0 && newStreak > 0) {
        dmg = dmg * 3;
        doAshFlash = true;
      }

      const acc = newTotalWords > 0 ? (newTotalWords / (newTotalWords + totalMisses)) * 100 : 100;

      // Codex: inject rare word at 15% chance when acc >= 90
      let injectRare = false;
      if (player.legion === 1 && acc >= 90 && Math.random() < 0.15) {
        injectRare = true;
      }

      setStreak(newStreak);
      setMultiplier(newMult);
      setTotalWords(newTotalWords);
      setTotalDmg(prev => prev + dmg);
      setMyDamage(prev => prev + dmg);
      setHitId(w.id);
      if (doAshFlash) {
        setAshFlash(true);
        setTimeout(() => setAshFlash(false), 400);
      }
      setTimeout(() => setHitId(null), 200);

      dispatchDamage(region.id, player.legion, dmg);
      setRegionHp(prev => Math.max(0, prev - dmg));

      const t = nowRef.current;
      setWords(prev => {
        const remaining = prev.filter((_, idx) => idx !== matchIdx);
        const newWord = injectRare
          ? makeWord(idCounter.current++, t, 4)
          : makeWord(idCounter.current++, t);
        return [...remaining, newWord];
      });
    } else {
      // Miss
      setStreak(0);
      setMultiplier(1);
      setTotalMisses(prev => prev + 1);
      setShaking(true);
      setTimeout(() => setShaking(false), 300);
    }

    setInput('');
  }, [input, words, streak, multiplier, multCap, totalWords, totalMisses, player, region, dispatchDamage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      submitWord();
    }
    // Solari backspace grace (500ms): allow backspace always
  }, [submitWord]);

  const elapsed = (now - startTime) / 1000 / 60; // minutes
  const wpm = elapsed > 0 ? Math.round(totalWords / elapsed) : 0;
  const acc = totalWords + totalMisses > 0 ? Math.round((totalWords / (totalWords + totalMisses)) * 100) : 100;

  const hpPct = (regionHp / region.enemy_max_hp) * 100;
  const totalContrib = region.damage_0 + region.damage_1 + region.damage_2 + region.damage_3 + region.damage_4 + myDamage;

  // Build matching word from input
  const matchingWord = input.length > 0
    ? words.find(w => w.text.startsWith(input.toLowerCase()))
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
            <span className="hud-val">{myDamage.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Region HP */}
      <div className="region-hp-wrap">
        <div className="region-hp-meta">
          <div>
            <p className="ss-label" style={{ color: 'var(--brand-muted)', marginBottom: 4 }}>{region.name}</p>
            <div className="hp-numbers">
              <span className="hp-current">{regionHp.toLocaleString()}</span>
              <span className="hp-sep">/</span>
              <span className="hp-max">{region.enemy_max_hp.toLocaleString()}</span>
            </div>
          </div>
          <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>
            {region.active_players} fighters · {region.active_wardens} wardens
          </span>
        </div>
        <div className="hp-bar-outer">
          <div className="hp-bar-inner" style={{ width: `${hpPct}%` }} />
        </div>

        {/* Contribution bar */}
        <div className="contrib-bar">
          {([0, 1, 2, 3, 4] as LegionId[]).map(id => {
            const dmg = (region[`damage_${id}` as keyof Region] as number) + (id === player.legion ? myDamage : 0);
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
            const dmg = (region[`damage_${id}` as keyof Region] as number) + (id === player.legion ? myDamage : 0);
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
        {words.slice(0, 8).map(w => {
          const lifeLeft = Math.max(0, w.expires_at - now);
          const lifePct = (lifeLeft / 5000) * 100;
          const isMatching = matchingWord?.id === w.id;
          const isHit = hitId === w.id;
          const isUrgent = lifeLeft < 1500 && !isHit;
          const typed = isMatching ? input.toLowerCase() : '';
          const rest = isMatching ? w.text.slice(typed.length) : w.text;

          return (
            <div
              key={w.id}
              className={[
                'word-card',
                `diff-${w.difficulty}`,
                isMatching ? 'matching' : '',
                isUrgent ? 'urgent' : '',
                isHit ? 'hit' : '',
              ].filter(Boolean).join(' ')}
            >
              <div>
                <div className="word-meta">
                  {player.legion === 4 ? (
                    <span className="word-diff">d{w.difficulty}</span>
                  ) : (
                    <span className="word-diff">·</span>
                  )}
                  <span className="word-dmg">{w.base_damage}dmg</span>
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
          <span className="streak-num">{streak}</span>
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
          <span className="streak-num">{multiplier.toFixed(2)}×</span>
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
