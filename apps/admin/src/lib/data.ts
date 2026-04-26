export type CommentStatus = 'pending' | 'flagged' | 'approved' | 'rejected';
export type ServiceStatus = 'running' | 'unhealthy' | 'stopped' | 'starting';

export type Comment = {
  id: string;
  status: CommentStatus;
  author: string;
  post: string;
  body: string;
  createdAt: string;
};

export type Service = {
  container: string;
  name: string;
  status: ServiceStatus;
  uptime: string;
  uptimeMin: number;
  mem: string;
  memBytes: number;
  image: string;
};

export type Legion = {
  id: string;
  name: string;
  color: string;
  regions: number;
  damage: number;
  players: number;
};

export type Region = {
  name: string;
  legion: string;
  hp: number;
  hpMax: number;
  contested?: boolean;
};

export type ActivityItem = {
  kind: string;
  time: string;
  text: string;
  legion: string;
};

export type Battle = {
  player: string;
  legion: string;
  region: string;
  startedMin: number;
  words: number;
  damage: number;
};

export type LogLine = {
  ts: string;
  text: string;
};

export const TIME_NOW = new Date('2026-04-26T14:32:00Z').getTime();

const ago = (mins: number) => new Date(TIME_NOW - mins * 60000).toISOString();

export const relTime = (iso: string): string => {
  const diff = (TIME_NOW - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

export const COMMENTS: Comment[] = [
  { id: 'c1', status: 'pending', author: 'devon.k', post: 'shipping-sasta-monorepos', body: "Curious how you handle env vars across the subdomains — do you bake them per-app or use a shared runtime config service?", createdAt: ago(8) },
  { id: 'c2', status: 'flagged', author: 'anonymous', post: 'why-i-stopped-using-vercel', body: "this is just shilling for self-hosting nobody asked. delete this", createdAt: ago(22) },
  { id: 'c3', status: 'pending', author: 'priya.s', post: 'rocm-on-a-thinkpad', body: "Did you have to build PyTorch from source for the 7900 XT? I've been trying to get this working for a week with the prebuilt wheels and it crashes every time on the first .cuda() call.", createdAt: ago(41) },
  { id: 'c4', status: 'pending', author: 'k.bhatia', post: 'shipping-sasta-monorepos', body: "Loved the post. The deploy.yml change-detection bit is exactly what we needed for our team.", createdAt: ago(67) },
  { id: 'c5', status: 'flagged', author: 'rafael_oss', post: 'typewars-postmortem', body: "buy followers cheap dm me telegram @rfl_growth_2026", createdAt: ago(74) },
  { id: 'c6', status: 'approved', author: 'mei.lin', post: 'rocm-on-a-thinkpad', body: "Worked perfectly on my 7800X variant after I bumped HSA_OVERRIDE_GFX_VERSION. Thanks for writing this.", createdAt: ago(122) },
  { id: 'c7', status: 'pending', author: 'jordan.t', post: 'why-i-stopped-using-vercel', body: "Have you tried Coolify? Curious what tipped you toward writing your own nginx + compose vs adopting an existing PaaS.", createdAt: ago(143) },
  { id: 'c8', status: 'approved', author: 'sam.r', post: 'typewars-postmortem', body: "The bit about word ownership being a CRDT problem disguised as a typing game made me actually laugh out loud. Genius framing.", createdAt: ago(180) },
  { id: 'c9', status: 'rejected', author: 'anonymous', post: 'shipping-sasta-monorepos', body: "first lol", createdAt: ago(240) },
  { id: 'c10', status: 'approved', author: 'aditya.v', post: 'rocm-on-a-thinkpad', body: "Bookmarking this. I keep meaning to wipe the spare ThinkPad and try ROCm.", createdAt: ago(310) },
];

export const SERVICES: Service[] = [
  { container: 'sastaspace-stdb', name: 'SpacetimeDB', status: 'running', uptime: '6d 4h 12m', uptimeMin: 8892, mem: '124 MB', memBytes: 130023424, image: 'clockworklabs/spacetime:1.0.0' },
  { container: 'sastaspace-auth', name: 'Auth Service', status: 'running', uptime: '2h 17m', uptimeMin: 137, mem: '38 MB', memBytes: 39845888, image: 'sastaspace-auth:local' },
  { container: 'sastaspace-notes', name: 'Notes', status: 'running', uptime: '1d 19h 04m', uptimeMin: 2584, mem: '52 MB', memBytes: 54525952, image: 'nginx:1.29-alpine' },
  { container: 'sastaspace-landing', name: 'Landing', status: 'running', uptime: '3d 22h 41m', uptimeMin: 5681, mem: '41 MB', memBytes: 43003904, image: 'nginx:1.29-alpine' },
  { container: 'sastaspace-typewars', name: 'TypeWars', status: 'running', uptime: '11h 06m', uptimeMin: 666, mem: '67 MB', memBytes: 70254592, image: 'nginx:1.29-alpine' },
  { container: 'sastaspace-moderator', name: 'Moderator', status: 'unhealthy', uptime: '14m', uptimeMin: 14, mem: '186 MB', memBytes: 195035136, image: 'sastaspace-moderator:local' },
];

export const CPU_HISTORY: number[] = [12, 14, 18, 22, 19, 17, 24, 28, 31, 27, 25, 22, 26, 30, 34, 38, 41, 37, 33, 29, 32, 36, 41, 45, 42, 38, 35, 39, 44, 48, 52, 49, 46, 43, 47, 51, 55, 58, 56, 53, 50, 54, 58, 62, 59, 55, 51, 48, 52, 56, 61, 64, 60, 57, 53, 50, 54, 58, 61, 67];
export const MEM_HISTORY_GB: number[] = [4.2, 4.3, 4.3, 4.4, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 7.0, 7.0, 6.9, 6.8, 6.7, 6.6, 6.7, 6.8, 6.9, 7.0, 7.1, 7.2, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9];

function genSeries(base: number, variance: number, n = 60): number[] {
  let v = base;
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    v += (Math.sin(i * 0.3) + (Math.random() - 0.5)) * variance;
    v = Math.max(0, Math.min(100, v));
    out.push(Number(v.toFixed(1)));
  }
  return out;
}
export const NET_TX: number[] = genSeries(2.4, 1.8);
export const NET_RX: number[] = genSeries(4.1, 2.4);

export const SYSTEM = {
  cpu: { pct: 67, cores: 16 },
  mem: { used: 8.9, total: 32, pct: 27.8, swapUsed: 124, swapTotal: 2048 },
  disk: { used: 142, total: 500, pct: 28.4, mount: '/' },
  gpu: { pct: 41, vramUsed: 4096, vramTotal: 24576, temp: 62, model: 'AMD Radeon RX 7900 XT' },
};

export const LEGIONS: Legion[] = [
  { id: 'crimson', name: 'Crimson Tide', color: '#c05621', regions: 8, damage: 142850, players: 23 },
  { id: 'verdant', name: 'Verdant Pact', color: '#4a7c3f', regions: 6, damage: 118420, players: 19 },
  { id: 'azure', name: 'Azure Order', color: '#3a6280', regions: 4, damage: 87340, players: 14 },
  { id: 'obsidian', name: 'Obsidian Cabal', color: '#3a3633', regions: 2, damage: 41280, players: 8 },
];

export const REGIONS: Region[] = [
  { name: 'Aravali', legion: 'crimson', hp: 720, hpMax: 1000 },
  { name: 'Konkan', legion: 'crimson', hp: 950, hpMax: 1000 },
  { name: 'Deccan', legion: 'crimson', hp: 410, hpMax: 1000, contested: true },
  { name: 'Malabar', legion: 'crimson', hp: 880, hpMax: 1000 },
  { name: 'Coromandel', legion: 'verdant', hp: 640, hpMax: 1000 },
  { name: 'Kathiawar', legion: 'verdant', hp: 920, hpMax: 1000 },
  { name: 'Vindhyas', legion: 'verdant', hp: 380, hpMax: 1000, contested: true },
  { name: 'Sundarbans', legion: 'azure', hp: 770, hpMax: 1000 },
  { name: 'Brahmaputra', legion: 'azure', hp: 690, hpMax: 1000 },
  { name: 'Pamir', legion: 'obsidian', hp: 540, hpMax: 1000 },
  { name: 'Karakoram', legion: 'crimson', hp: 830, hpMax: 1000 },
  { name: 'Punjab', legion: 'verdant', hp: 920, hpMax: 1000 },
  { name: 'Kashmir', legion: 'crimson', hp: 1000, hpMax: 1000 },
  { name: 'Sindh', legion: 'azure', hp: 600, hpMax: 1000 },
  { name: 'Bengal', legion: 'verdant', hp: 480, hpMax: 1000 },
  { name: 'Tibet', legion: 'obsidian', hp: 280, hpMax: 1000, contested: true },
  { name: 'Nilgiris', legion: 'crimson', hp: 870, hpMax: 1000 },
  { name: 'Chota Nagpur', legion: 'crimson', hp: 720, hpMax: 1000 },
  { name: 'Hadoti', legion: 'verdant', hp: 660, hpMax: 1000 },
  { name: 'Rann', legion: 'azure', hp: 510, hpMax: 1000 },
];

export const ACTIVITY: ActivityItem[] = [
  { kind: 'word', time: ago(0.05), text: "ananya.k typed 'serendipity' in Deccan for 18 dmg", legion: 'crimson' },
  { kind: 'word', time: ago(0.18), text: "rohan_99 typed 'parenthetical' in Vindhyas for 22 dmg", legion: 'verdant' },
  { kind: 'battle', time: ago(0.45), text: "Battle started in Tibet", legion: 'obsidian' },
  { kind: 'word', time: ago(0.7), text: "tara.m typed 'crystalline' in Bengal for 14 dmg", legion: 'verdant' },
  { kind: 'capture', time: ago(1.2), text: "Hadoti captured by Verdant Pact", legion: 'verdant' },
  { kind: 'word', time: ago(1.6), text: "ishan.p typed 'vermillion' in Konkan for 12 dmg", legion: 'crimson' },
  { kind: 'word', time: ago(2.1), text: "anaya_t typed 'mnemonic' in Sundarbans for 16 dmg", legion: 'azure' },
  { kind: 'battle', time: ago(2.4), text: "Battle ended in Karakoram", legion: 'crimson' },
  { kind: 'word', time: ago(3.0), text: "vikram.s typed 'bureaucracy' in Tibet for 24 dmg", legion: 'obsidian' },
  { kind: 'word', time: ago(3.4), text: "neha.b typed 'kaleidoscope' in Vindhyas for 26 dmg", legion: 'verdant' },
  { kind: 'word', time: ago(3.9), text: "arjun.k typed 'opaline' in Aravali for 11 dmg", legion: 'crimson' },
  { kind: 'capture', time: ago(4.4), text: "Bengal captured by Verdant Pact", legion: 'verdant' },
  { kind: 'word', time: ago(5.0), text: "diya.r typed 'phosphorescent' in Punjab for 28 dmg", legion: 'verdant' },
  { kind: 'word', time: ago(5.6), text: "kunal.j typed 'triumvirate' in Deccan for 21 dmg", legion: 'crimson' },
  { kind: 'word', time: ago(6.2), text: "sara.h typed 'archipelago' in Sundarbans for 23 dmg", legion: 'azure' },
];

export const ACTIVE_BATTLES: Battle[] = [
  { player: 'ananya.k', legion: 'crimson', region: 'Deccan', startedMin: 4, words: 38, damage: 482 },
  { player: 'rohan_99', legion: 'verdant', region: 'Vindhyas', startedMin: 7, words: 52, damage: 691 },
  { player: 'vikram.s', legion: 'obsidian', region: 'Tibet', startedMin: 2, words: 14, damage: 218 },
  { player: 'tara.m', legion: 'verdant', region: 'Bengal', startedMin: 11, words: 71, damage: 944 },
  { player: 'arjun.k', legion: 'crimson', region: 'Aravali', startedMin: 1, words: 6, damage: 88 },
];

export const LOG_TEMPLATES: Record<string, LogLine[]> = {
  'sastaspace-stdb': [
    { ts: '14:31:58.124', text: 'INFO  reducer  comment_create completed in 2.3ms (caller=0xa1f...)' },
    { ts: '14:31:57.882', text: 'DEBUG ws       client 0xa1f4 subscribed to comment, post' },
    { ts: '14:31:55.401', text: 'INFO  reducer  word_submit completed in 1.1ms' },
    { ts: '14:31:54.220', text: 'INFO  reducer  battle_tick completed in 4.7ms' },
    { ts: '14:31:50.117', text: 'DEBUG ws       client 0xc2b1 connected from 198.51.100.42' },
    { ts: '14:31:48.330', text: 'INFO  reducer  word_submit completed in 0.9ms' },
    { ts: '14:31:46.901', text: 'WARN  scheduler battle_tick took 8.2ms (above 5ms target)' },
    { ts: '14:31:45.012', text: 'INFO  reducer  region_capture(Hadoti, verdant) completed in 3.4ms' },
    { ts: '14:31:42.778', text: 'INFO  reducer  word_submit completed in 1.0ms' },
    { ts: '14:31:40.115', text: 'DEBUG ws       client 0x18ed disconnected' },
    { ts: '14:31:38.554', text: 'INFO  reducer  comment_create completed in 1.9ms' },
    { ts: '14:31:36.089', text: 'INFO  reducer  presence_heartbeat completed in 0.4ms' },
    { ts: '14:31:34.221', text: 'WARN  ws       slow client 0x44a2 — backpressure 12ms' },
    { ts: '14:31:32.018', text: 'INFO  reducer  battle_start(Tibet, obsidian, vikram.s) completed in 5.1ms' },
    { ts: '14:31:30.005', text: 'DEBUG storage  flushed 142 events to wal' },
  ],
  'sastaspace-auth': [
    { ts: '14:31:48.220', text: 'INFO  request  POST /auth/request status=200 email=mohitkhare582@gmail.com 47ms' },
    { ts: '14:31:48.182', text: 'DEBUG mailer   sending magic link to mohitkhare582@gmail.com via Resend' },
    { ts: '14:31:42.110', text: 'INFO  request  GET /auth/verify status=302 token=** 12ms' },
    { ts: '14:31:30.554', text: 'INFO  request  POST /auth/request status=200 email=jordan.t@example.com 41ms' },
    { ts: '14:30:55.119', text: 'WARN  ratelimit email=anonymous@spam.test exceeded 5/min — temporarily blocked' },
    { ts: '14:30:42.001', text: 'INFO  request  POST /auth/request status=429 9ms' },
    { ts: '14:29:18.220', text: 'ERROR mailer   resend api returned 503; retrying in 2s' },
    { ts: '14:29:20.224', text: 'INFO  mailer   resend api recovered; retry succeeded' },
    { ts: '14:28:01.555', text: 'INFO  startup  bound to 127.0.0.1:3120; ADMIN_CALLBACK=https://admin.sastaspace.com/auth/callback' },
  ],
  'sastaspace-notes': [
    { ts: '14:31:55.001', text: 'INFO  127.0.0.1 - - "GET / HTTP/1.1" 200 14821' },
    { ts: '14:31:54.122', text: 'INFO  127.0.0.1 - - "GET /shipping-sasta-monorepos HTTP/1.1" 200 22118' },
    { ts: '14:31:42.901', text: 'INFO  127.0.0.1 - - "GET /rocm-on-a-thinkpad HTTP/1.1" 200 18402' },
    { ts: '14:31:30.004', text: 'INFO  127.0.0.1 - - "GET /admin/comments HTTP/1.1" 200 3214' },
    { ts: '14:31:28.115', text: 'WARN  127.0.0.1 - - "GET /admin/comments HTTP/1.1" 200 3214 (isOwnerSignedIn=false)' },
    { ts: '14:31:14.220', text: 'INFO  127.0.0.1 - - "GET /feed.xml HTTP/1.1" 200 8901' },
  ],
  'sastaspace-landing': [
    { ts: '14:31:40.001', text: 'INFO  127.0.0.1 - - "GET / HTTP/1.1" 200 4129' },
    { ts: '14:31:18.220', text: 'INFO  127.0.0.1 - - "GET /assets/wordmark.svg HTTP/1.1" 200 2104' },
    { ts: '14:30:55.110', text: 'INFO  127.0.0.1 - - "GET /robots.txt HTTP/1.1" 200 41' },
    { ts: '14:29:01.001', text: 'INFO  127.0.0.1 - - "GET / HTTP/1.1" 200 4129' },
  ],
  'sastaspace-typewars': [
    { ts: '14:31:50.111', text: 'INFO  127.0.0.1 - - "GET /play HTTP/1.1" 200 18820' },
    { ts: '14:31:42.115', text: 'INFO  127.0.0.1 - - "GET /api/word/next HTTP/1.1" 200 142' },
    { ts: '14:31:30.004', text: 'INFO  127.0.0.1 - - "POST /api/word/submit HTTP/1.1" 200 88' },
    { ts: '14:31:18.220', text: 'INFO  127.0.0.1 - - "GET /map HTTP/1.1" 200 12410' },
  ],
  'sastaspace-moderator': [
    { ts: '14:31:58.330', text: 'ERROR llm.client connection to ollama:11434 timed out after 30s' },
    { ts: '14:31:55.012', text: 'WARN  health   skipping check — last 3 LLM calls failed' },
    { ts: '14:31:50.114', text: 'ERROR moderate failed to classify comment c2 (anonymous): backend unavailable' },
    { ts: '14:31:42.901', text: 'WARN  retry    backing off 4.0s before next attempt' },
    { ts: '14:31:38.001', text: 'ERROR llm.client connection to ollama:11434 timed out after 30s' },
    { ts: '14:31:30.554', text: 'DEBUG queue    pending=12 inflight=0' },
    { ts: '14:31:28.115', text: 'INFO  startup  bound to 127.0.0.1:3170; OLLAMA_HOST=http://ollama:11434' },
  ],
};
