export type LegionId = 0 | 1 | 2 | 3 | 4;

export interface Region {
  id: number;
  name: string;
  tier: 1 | 2 | 3;
  controlling_legion: -1 | LegionId;
  enemy_hp: number;
  enemy_max_hp: number;
  regen_rate: number;
  damage_0: number;
  damage_1: number;
  damage_2: number;
  damage_3: number;
  damage_4: number;
  active_wardens: number;
  active_players: number;
}

export interface Player {
  legion: LegionId;
  username: string;
  total_damage: number;
  season_damage: number;
  best_wpm: number;
  email?: string;
}

export interface LiberatedInfo {
  region: Region;
  winner: LegionId;
}

export type Screen = 'legion-select' | 'warmap' | 'battle' | 'liberated' | 'leaderboard';

export interface WordState {
  id: number;
  text: string;
  difficulty: number;
  base_damage: number;
  spawned_at: number;
  expires_at: number;
}
