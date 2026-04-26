'use client';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { useSpacetimeDB, useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/typewars-bindings';
import type { Screen, Player, Region, LiberatedInfo, LegionId } from '@/types';
import { makeRegions } from '@/lib/regions';
import { toPlayer } from '@/lib/adapters';
import LegionSelect from './LegionSelect';
import MapWarMap from './MapWarMap';
import Battle from './Battle';
import LiberatedSplash from './LiberatedSplash';
import Leaderboard from './Leaderboard';
import LegionSwapModal from './LegionSwapModal';

function setupRegions(base: Region[]): Region[] {
  const r = base.map(region => ({ ...region }));
  r[0] = { ...r[0], controlling_legion: 0, enemy_hp: 0, damage_0: r[0].enemy_max_hp };
  r[1] = { ...r[1], controlling_legion: 1, enemy_hp: 0, damage_1: r[1].enemy_max_hp };
  r[5] = { ...r[5], controlling_legion: 2, enemy_hp: 0, damage_2: r[5].enemy_max_hp };
  r[11] = { ...r[11], controlling_legion: 3, enemy_hp: 0, damage_3: r[11].enemy_max_hp };
  r[2] = { ...r[2], enemy_hp: Math.round(r[2].enemy_max_hp * 0.72), damage_0: Math.round(r[2].enemy_max_hp * 0.28) };
  r[3] = { ...r[3], enemy_hp: Math.round(r[3].enemy_max_hp * 0.55), damage_1: Math.round(r[3].enemy_max_hp * 0.45) };
  r[12] = { ...r[12], enemy_hp: Math.round(r[12].enemy_max_hp * 0.40), damage_2: Math.round(r[12].enemy_max_hp * 0.60) };
  r[20] = { ...r[20], enemy_hp: Math.round(r[20].enemy_max_hp * 0.85), damage_4: Math.round(r[20].enemy_max_hp * 0.15) };
  return r;
}

export default function App() {
  const { identity, isActive } = useSpacetimeDB();

  const playerQuery = useMemo(
    () => identity ? tables.player.where(p => p.identity.eq(identity)) : tables.player.where(() => false),
    [identity],
  );
  const [playerRows] = useTable(playerQuery);
  const playerRow = playerRows[0];

  const registerPlayer = useReducer(reducers.registerPlayer);

  const [screen, setScreen] = useState<Screen>('legion-select');
  const [regions, setRegions] = useState<Region[]>([]);
  const [activeRegion, setActiveRegion] = useState<Region | null>(null);
  const [liberatedInfo, setLiberatedInfo] = useState<LiberatedInfo | null>(null);
  const [swapOpen, setSwapOpen] = useState(false);

  const player: Player | null = playerRow ? toPlayer(playerRow) : null;

  useEffect(() => {
    if (player && screen === 'legion-select') {
      const base = makeRegions();
      setRegions(setupRegions(base));
      setScreen('warmap');
    }
  }, [player, screen]);

  const chooseLegion = useCallback(async (legion: LegionId, username: string) => {
    await registerPlayer({ username, legion });
  }, [registerPlayer]);

  const enterBattle = useCallback((r: Region) => {
    setActiveRegion(r);
    setScreen('battle');
  }, []);

  const dispatchDamage = useCallback((regionId: number, legion: LegionId, amount: number) => {
    setRegions(prev => prev.map(r => {
      if (r.id !== regionId) return r;
      const key = `damage_${legion}` as keyof Region;
      const newDmg = (r[key] as number) + amount;
      const newHp = Math.max(0, r.enemy_hp - amount);
      const updated: Region = { ...r, [key]: newDmg, enemy_hp: newHp };
      if (newHp === 0 && r.controlling_legion === -1) {
        const totalDamages = [updated.damage_0, updated.damage_1, updated.damage_2, updated.damage_3, updated.damage_4];
        const winner = totalDamages.indexOf(Math.max(...totalDamages)) as LegionId;
        updated.controlling_legion = winner;
      }
      return updated;
    }));
  }, []);

  const exitBattle = useCallback(() => {
    if (!activeRegion || !player) { setScreen('warmap'); return; }
    const current = regions.find(r => r.id === activeRegion.id);
    if (current && current.controlling_legion !== -1 && activeRegion.controlling_legion === -1) {
      const damages = [current.damage_0, current.damage_1, current.damage_2, current.damage_3, current.damage_4];
      const winner = damages.indexOf(Math.max(...damages)) as LegionId;
      const contributors = [
        { name: player.username, legion: player.legion, damage: player.season_damage },
        { name: 'vex_prime', legion: 0 as LegionId, damage: Math.floor(Math.random() * 50000) + 10000 },
        { name: 'cipher_9', legion: 1 as LegionId, damage: Math.floor(Math.random() * 40000) + 8000 },
        { name: 'surge_x', legion: 3 as LegionId, damage: Math.floor(Math.random() * 30000) + 5000 },
      ];
      setLiberatedInfo({ region: current, winner, contributors });
      setScreen('liberated');
    } else {
      setScreen('warmap');
    }
    setActiveRegion(null);
  }, [activeRegion, player, regions]);

  const swapLegion = useCallback((_legion: LegionId) => {
    setSwapOpen(false);
  }, []);

  if (!isActive) {
    return (
      <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <span className="ss-terminal">connecting to typewars…</span>
      </div>
    );
  }

  if (screen === 'legion-select' && !player) {
    return <LegionSelect onChoose={chooseLegion} />;
  }

  if (!player) return null;

  if (screen === 'warmap') {
    return (
      <>
        <MapWarMap
          regions={regions}
          player={player}
          onEnter={enterBattle}
          onOpenBoard={() => setScreen('leaderboard')}
          onSwapLegion={() => setSwapOpen(true)}
        />
        {swapOpen && (
          <LegionSwapModal
            player={player}
            onClose={() => setSwapOpen(false)}
            onSwap={swapLegion}
          />
        )}
      </>
    );
  }

  if (screen === 'battle' && activeRegion) {
    return (
      <Battle
        player={player}
        region={activeRegion}
        onExit={exitBattle}
        dispatchDamage={dispatchDamage}
      />
    );
  }

  if (screen === 'liberated' && liberatedInfo) {
    return (
      <LiberatedSplash
        region={liberatedInfo.region}
        winner={liberatedInfo.winner}
        contributors={liberatedInfo.contributors}
        onContinue={() => { setLiberatedInfo(null); setScreen('warmap'); }}
      />
    );
  }

  if (screen === 'leaderboard') {
    return (
      <Leaderboard
        regions={regions}
        player={player}
        onBack={() => setScreen('warmap')}
      />
    );
  }

  return null;
}
