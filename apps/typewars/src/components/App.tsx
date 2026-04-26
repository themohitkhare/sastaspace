'use client';
import React, { useState, useCallback, useMemo } from 'react';
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
import { ProfileModal } from './ProfileModal';

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

  const [postLoginScreen, setPostLoginScreen] = useState<Exclude<Screen, 'legion-select'>>('warmap');
  const [activeRegion, setActiveRegion] = useState<Region | null>(null);
  const [liberatedInfo, setLiberatedInfo] = useState<LiberatedInfo | null>(null);
  const [swapOpen, setSwapOpen] = useState(false);
  const [profileUser, setProfileUser] = useState<string | null>(null);

  const player: Player | null = playerRow ? toPlayer(playerRow) : null;
  const screen: Screen = player ? postLoginScreen : 'legion-select';
  const setScreen = (s: Screen) => {
    if (s !== 'legion-select') setPostLoginScreen(s);
  };

  const chooseLegion = useCallback(async (legion: LegionId, username: string) => {
    await registerPlayer({ username, legion });
  }, [registerPlayer]);

  const enterBattle = useCallback((r: Region) => {
    setActiveRegion(r);
    setScreen('battle');
  }, []);

  const exitBattle = useCallback(() => {
    if (!activeRegion || !player) { setScreen('warmap'); return; }
    const current = regions.find(r => r.id === activeRegion.id);
    if (current && current.controlling_legion !== -1 && activeRegion.controlling_legion === -1) {
      const damages = [current.damage_0, current.damage_1, current.damage_2, current.damage_3, current.damage_4];
      const winner = damages.indexOf(Math.max(...damages)) as LegionId;
      setLiberatedInfo({ region: current, winner });
      setScreen('liberated');
    } else {
      setScreen('warmap');
    }
    setActiveRegion(null);
  }, [activeRegion, player, regions]);

  const swapLegion = useCallback(async (_legion: LegionId): Promise<void> => {
    // TODO: reducer doesn't exist yet — see audit-fix/typewars-perf
    // A `change_legion` (or equivalent) reducer needs to be added to the
    // typewars SpacetimeDB module before this can be wired up.
    // Once the reducer is generated into @sastaspace/typewars-bindings, replace
    // this no-op with:
    //   await changePlayerLegion({ legion: _legion });
    //   setSwapOpen(false);
    setSwapOpen(false);
  }, []);

  let screenContent: React.ReactNode;

  if (!isActive) {
    screenContent = (
      <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <span className="ss-terminal">connecting to typewars…</span>
      </div>
    );
  } else if (screen === 'legion-select' && !player) {
    screenContent = <LegionSelect onChoose={chooseLegion} />;
  } else if (!player) {
    screenContent = null;
  } else if (screen === 'warmap') {
    screenContent = (
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
  } else if (screen === 'battle' && activeRegion) {
    screenContent = (
      <Battle
        player={player}
        region={activeRegion}
        onExit={exitBattle}
      />
    );
  } else if (screen === 'liberated' && liberatedInfo) {
    screenContent = (
      <LiberatedSplash
        region={liberatedInfo.region}
        winner={liberatedInfo.winner}
        onContinue={() => { setLiberatedInfo(null); setScreen('warmap'); }}
      />
    );
  } else if (screen === 'leaderboard') {
    screenContent = (
      <Leaderboard
        regions={regions}
        player={player}
        onBack={() => setScreen('warmap')}
        onOpenProfile={setProfileUser}
      />
    );
  } else {
    screenContent = null;
  }

  return (
    <>
      {screenContent}
      {profileUser && (
        <ProfileModal
          username={profileUser}
          onClose={() => setProfileUser(null)}
        />
      )}
    </>
  );
}
