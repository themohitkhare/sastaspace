import { create } from 'zustand';

const CLASSES = {
  WARRIOR: { icon: '⚔️', desc: 'Brute force specialist', baseStats: { STR: 8, DEX: 4, INT: 2, WIS: 3, VIT: 8, LCK: 5 } },
  MAGE: { icon: '🔮', desc: 'Arcane devastation', baseStats: { STR: 2, DEX: 3, INT: 9, WIS: 7, VIT: 4, LCK: 5 } },
  ROGUE: { icon: '🗡️', desc: 'Shadows and daggers', baseStats: { STR: 4, DEX: 9, INT: 5, WIS: 3, VIT: 4, LCK: 5 } },
  RANGER: { icon: '🏹', desc: "Nature's marksman", baseStats: { STR: 5, DEX: 7, INT: 4, WIS: 6, VIT: 5, LCK: 3 } },
  NECRO: { icon: '💀', desc: 'Death is just the beginning', baseStats: { STR: 3, DEX: 3, INT: 8, WIS: 8, VIT: 3, LCK: 5 } },
  PALADIN: { icon: '🛡️', desc: 'Holy tank', baseStats: { STR: 6, DEX: 3, INT: 4, WIS: 6, VIT: 8, LCK: 3 } },
};

export const STAT_NAMES = ['STR', 'DEX', 'INT', 'WIS', 'VIT', 'LCK'];
export const TOTAL_BONUS_POINTS = 30;
export const STAT_MAX = 20;
export { CLASSES };

const DEFAULT_CLASS = 'WARRIOR';

function getInitialState() {
  return {
    heroClass: DEFAULT_CLASS,
    bonusStats: { STR: 0, DEX: 0, INT: 0, WIS: 0, VIT: 0, LCK: 0 },
    pointsSpent: 0,
  };
}

const useHeroStore = create((set, get) => ({
  ...getInitialState(),

  setClass: (heroClass) => {
    set({
      heroClass,
      bonusStats: { STR: 0, DEX: 0, INT: 0, WIS: 0, VIT: 0, LCK: 0 },
      pointsSpent: 0,
    });
  },

  incrementStat: (stat) => {
    const { bonusStats, pointsSpent } = get();
    const baseStats = CLASSES[get().heroClass].baseStats;
    const currentTotal = baseStats[stat] + bonusStats[stat];

    if (pointsSpent >= TOTAL_BONUS_POINTS) return;
    if (currentTotal >= STAT_MAX) return;

    set({
      bonusStats: { ...bonusStats, [stat]: bonusStats[stat] + 1 },
      pointsSpent: pointsSpent + 1,
    });
  },

  decrementStat: (stat) => {
    const { bonusStats, pointsSpent } = get();
    if (bonusStats[stat] <= 0) return;

    set({
      bonusStats: { ...bonusStats, [stat]: bonusStats[stat] - 1 },
      pointsSpent: pointsSpent - 1,
    });
  },

  setRandomHero: (heroClass, stats) => {
    const baseStats = CLASSES[heroClass].baseStats;
    const bonusStats = {};
    let spent = 0;
    for (const stat of STAT_NAMES) {
      bonusStats[stat] = stats[stat] - baseStats[stat];
      spent += bonusStats[stat];
    }
    set({ heroClass, bonusStats, pointsSpent: spent });
  },

  reset: () => set(getInitialState()),

  getStats: () => {
    const { heroClass, bonusStats } = get();
    const baseStats = CLASSES[heroClass].baseStats;
    const stats = {};
    for (const stat of STAT_NAMES) {
      stats[stat] = baseStats[stat] + bonusStats[stat];
    }
    return stats;
  },

  getTotalPower: () => {
    const stats = get().getStats();
    return Object.values(stats).reduce((sum, v) => sum + v, 0);
  },

  getPointsRemaining: () => {
    return TOTAL_BONUS_POINTS - get().pointsSpent;
  },
}));

export default useHeroStore;
