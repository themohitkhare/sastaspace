import type { WordState } from '@/types';

export const WORD_POOLS: Record<number, string[]> = {
  1: ['ash','core','void','ion','flux','warp','sun','star','moon','dawn','rift','hex','arc','orb','nova','dust','glow','ember','spark','tide','helm','axis','beam','byte','cell','code','data','echo','gate','grid','halo','iron','lens','mark','node','path','pulse','quad','rune'],
  2: ['signal','vector','plasma','quasar','cluster','orbital','reactor','sector','console','protocol','runtime','channel','beacon','gravity','horizon','liberty','machine','nucleus','outpost','planet','quantum','radiant','silicon','terminal','uplink','vacuum','warden','zenith','arcane','binary','cipher','daemon'],
  3: ['hyperspace','singularity','asymptotic','catastrophe','dreadnought','equilibrium','federation','gravitation','hexadecimal','illumination','jurisdiction','kilometers','liberation','macrocosmic','nightingale','occupation','perpendicular','quartermaster','reverberation','synchronized'],
  4: ['recursion','algorithm','heuristic','telemetry','continuum','axiomatic','holographic','luminescent'],
};

export function makeWord(idCounter: number, t: number, diff?: number): WordState {
  if (!diff) { const r = Math.random(); diff = r < 0.625 ? 1 : r < 0.875 ? 2 : 3; }
  const pool = WORD_POOLS[diff];
  const text = pool[(idCounter * 9301 + 49297) % pool.length];
  const baseDamage = ({ 1: 10, 2: 25, 3: 50, 4: 100 } as Record<number,number>)[diff];
  return { id: idCounter, text, difficulty: diff, base_damage: baseDamage, spawned_at: t, expires_at: t + 5000 };
}
