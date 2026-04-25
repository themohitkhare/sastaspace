import type { Region } from '@/types';

const REGION_NAMES = [
  'Helia Drift','Tarn Belt','Ophir Veil','Murex Ring','Quill Reach','Vex Hollow','Ire Span','Pall Verge','Cynth Edge','Brail Mote',
  'Khoros Span','Aelin Shore','Nephesh','Talos Gate','Vorm Crucible','Iridia','Pellan Spires','Solune','Ushar Vault','Rhetic Loom',
  'Astron Heart','Vasari Throne','Ophanim','Mahala Eye','Indra Crown',
];
const TIERS = { 1: { max: 50000, regen: 200 }, 2: { max: 100000, regen: 500 }, 3: { max: 250000, regen: 1500 } };

export function makeRegions(): Region[] {
  return Array.from({ length: 25 }, (_, i) => {
    const tier = (i < 10 ? 1 : i < 20 ? 2 : 3) as 1|2|3;
    const t = TIERS[tier];
    return { id: i, name: REGION_NAMES[i], tier, controlling_legion: -1 as -1, enemy_hp: t.max, enemy_max_hp: t.max,
      regen_rate: t.regen, damage_0: 0, damage_1: 0, damage_2: 0, damage_3: 0, damage_4: 0,
      active_wardens: Math.floor(Math.random() * 5), active_players: Math.floor(Math.random() * 30) + 2 };
  });
}

export const MAP_REGIONS = [
  {x:120,y:120},{x:280,y:90},{x:980,y:110},{x:1100,y:220},{x:1140,y:480},
  {x:1050,y:680},{x:720,y:720},{x:380,y:720},{x:140,y:620},{x:90,y:360},
  {x:320,y:250},{x:540,y:180},{x:800,y:220},{x:950,y:360},{x:880,y:540},
  {x:700,y:600},{x:480,y:580},{x:280,y:480},{x:220,y:350},{x:600,y:320},
  {x:480,y:400},{x:620,y:440},{x:560,y:360},{x:700,y:380},{x:580,y:510},
];

export const CONTINENTS: [number,number][][] = [
  [[60,80],[200,60],[340,80],[420,160],[400,260],[300,300],[180,280],[80,220]],
  [[700,90],[900,70],[1080,100],[1160,200],[1140,320],[1020,300],[880,260],[760,200]],
  [[400,330],[560,300],[720,310],[820,400],[760,540],[600,580],[440,560],[360,460]],
  [[860,440],[1000,460],[1100,540],[1080,680],[940,720],[820,640]],
  [[100,460],[260,440],[360,540],[340,680],[200,720],[80,640]],
  [[460,640],[600,620],[720,680],[640,740],[500,740]],
  [[40,300],[120,280],[140,360],[80,380]],
];
