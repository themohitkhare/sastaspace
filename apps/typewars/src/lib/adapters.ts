import type { Player, LegionId, Region } from '@/types';

type RegionRow = {
  id: number;
  name: string;
  tier: number;
  controllingLegion: number;
  enemyHp: bigint;
  enemyMaxHp: bigint;
  regenRate: bigint;
  damage0: bigint;
  damage1: bigint;
  damage2: bigint;
  damage3: bigint;
  damage4: bigint;
  activeWardens: number;
};

export function toRegion(row: RegionRow, activePlayers = 0): Region {
  return {
    id: row.id,
    name: row.name,
    tier: row.tier as 1 | 2 | 3,
    controlling_legion: row.controllingLegion as Region['controlling_legion'],
    enemy_hp: Number(row.enemyHp),
    enemy_max_hp: Number(row.enemyMaxHp),
    regen_rate: Number(row.regenRate),
    damage_0: Number(row.damage0),
    damage_1: Number(row.damage1),
    damage_2: Number(row.damage2),
    damage_3: Number(row.damage3),
    damage_4: Number(row.damage4),
    active_wardens: row.activeWardens,
    active_players: activePlayers,
  };
}


type PlayerRow = {
  identity: unknown;
  username: string;
  legion: number;
  totalDamage: bigint;
  seasonDamage: bigint;
  bestWpm: number;
};

export function toPlayer(row: PlayerRow): Player {
  return {
    legion: row.legion as LegionId,
    username: row.username,
    total_damage: Number(row.totalDamage),
    season_damage: Number(row.seasonDamage),
    best_wpm: row.bestWpm,
  };
}
