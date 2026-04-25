export const LEGION_INFO: Record<number, { name: string; color: string; text: string; short: string; mechanic: string }> = {
  0: { name: 'Ashborn',   color: '#c64b2a', text: 'Every 10-word streak: next word deals 3× damage', short: 'ASH', mechanic: 'Pyrocharge' },
  1: { name: 'The Codex', color: '#c89b3c', text: '≥90% accuracy spawns rare high-damage words',      short: 'CDX', mechanic: 'Verity' },
  2: { name: 'Wardens',   color: '#3d8a8a', text: '3+ Wardens in a region halves enemy regen',        short: 'WRD', mechanic: 'Bulwark' },
  3: { name: 'Surge',     color: '#7a4ab8', text: 'Multiplier cap raised from 3.0× to 5.0×',          short: 'SRG', mechanic: 'Overdrive' },
  4: { name: 'Solari',    color: '#d4b94a', text: 'Difficulty shown; 500ms backspace grace',           short: 'SOL', mechanic: 'Clarity' },
};
