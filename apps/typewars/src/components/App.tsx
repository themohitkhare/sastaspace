'use client';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { useSpacetimeDB, useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/typewars-bindings';
import type { Screen, Player, Region, LiberatedInfo, LegionId } from '@/types';
import { toPlayer, toRegion } from '@/lib/adapters';
import LegionSelect from './LegionSelect';
import MapWarMap from './MapWarMap';
import Battle from './Battle';
import LiberatedSplash from './LiberatedSplash';
import Leaderboard from './Leaderboard';
import LegionSwapModal from './LegionSwapModal';

export default function App() {
  const { identity, isActive } = useSpacetimeDB();

  const playerQuery = useMemo(
    () => identity ? tables.player.where(p => p.identity.eq(identity)) : tables.player.where(() => false),
    [identity],
  );
  const [playerRows] = useTable(playerQuery);
  const playerRow = playerRows[0];

  const registerPlayer = useReducer(reducers.registerPlayer);

  const [regionRows] = useTable(tables.region);
  const regions: Region[] = useMemo(
    () => [...regionRows].sort((a, b) => a.id - b.id).map(r => toRegion(r)),
    [regionRows],
  );

  const [screen, setScreen] = useState<Screen>('legion-select');
  const [activeRegion, setActiveRegion] = useState<Region | null>(null);
  const [liberatedInfo, setLiberatedInfo] = useState<LiberatedInfo | null>(null);
  const [swapOpen, setSwapOpen] = useState(false);

  const player: Player | null = playerRow ? toPlayer(playerRow) : null;

  useEffect(() => {
    if (player && screen === 'legion-select') {
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

  const dispatchDamage = useCallback((_regionId: number, _legion: LegionId, _amount: number) => {
    // Server-authoritative: damage is applied by the submit_word reducer and
    // streamed back via the region subscription. Kept as a no-op for the
    // existing Battle prop contract until step 4 finishes the hot path.
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
