import type { Player, LegionId } from '@/types';

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
