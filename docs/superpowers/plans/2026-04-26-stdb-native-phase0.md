# Phase 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (this phase is sequential, no parallel agents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay every prerequisite for the SpacetimeDB-native rewire — directory renames, workers skeleton, LocalAI on taxila, baseline E2E green — without changing any user-facing behavior.

**Architecture:** Pure bootstrap. No reducers added, no frontends rewired, no Python services deleted. End state should be functionally identical to the start, with a different file layout and one new infra service (LocalAI) idling.

**Tech Stack:** Rust + Cargo (module rename), Node 22 + pnpm (workers skeleton), Docker Compose (LocalAI), Playwright (E2E baseline).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "Migration phases / Phase 0"

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

---

## Task 1: Audit current paths that hardcode `module/` or `game/`

**Files:**
- Read: workspace `Cargo.toml`, all `.github/workflows/*.yml`, root `package.json`, `pnpm-workspace.yaml`, `infra/docker-compose.yml`, any `scripts/*` referenced.

- [ ] **Step 1: Find every reference**

```bash
cd /Users/mkhare/Development/sastaspace
grep -rn --include='*.toml' --include='*.yml' --include='*.yaml' --include='*.json' --include='*.sh' --include='*.md' \
  -e '\bmodule/\b' -e '\bgame/\b' \
  --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.next --exclude-dir=graphify-out \
  | grep -v 'node_modules' | tee /tmp/path-refs.txt
```

Expected: a focused list of files mentioning `module/` or `game/`. Save to `/tmp/path-refs.txt` for later cross-check.

- [ ] **Step 2: Inspect each hit and write a rename mapping**

For each file in `/tmp/path-refs.txt`, note:
- Does the path need to change to `modules/sastaspace/` or `modules/typewars/`?
- Or is it documentation that should mention the new path?

Write findings to `/tmp/path-refs-decisions.md` (throwaway) so Task 2 has the complete edit list.

- [ ] **Step 3: Commit the audit notes (optional skip)**

If `/tmp/path-refs-decisions.md` is useful for the team, copy it to `docs/audits/2026-04-26-rename-prep.md` and commit. Otherwise discard. No code changes in this task.

---

## Task 2: Rename `module/` → `modules/sastaspace/`

**Files:**
- Move: `module/` → `modules/sastaspace/`
- Modify: workspace `Cargo.toml`, `infra/docker-compose.yml`, any scripts found in Task 1

- [ ] **Step 1: Create the new parent and git-mv the directory**

```bash
mkdir -p modules
git mv module modules/sastaspace
```

Expected: `git status` shows the rename as `R  module/...` → `modules/sastaspace/...` for every file.

- [ ] **Step 2: Update the root Cargo workspace manifest**

Edit `Cargo.toml` at repo root. Find the `[workspace]` `members = [...]` section. Replace `"module"` with `"modules/sastaspace"`. Leave `"game"` for Task 3.

```toml
[workspace]
members = ["modules/sastaspace", "game"]
resolver = "2"
```

(If there's no root Cargo workspace and `module/Cargo.toml` was standalone, then `modules/sastaspace/Cargo.toml` already works as-is and this step is a no-op. Check first with `cat Cargo.toml 2>/dev/null || echo 'no root Cargo.toml'`.)

- [ ] **Step 3: Update docker-compose volume paths**

Edit `infra/docker-compose.yml`. The `spacetime` service's volumes likely reference `./module` for the published WASM. Search for any `./module` and update if present.

```bash
grep -n 'module' infra/docker-compose.yml
```

Replace any `./module` → `../modules/sastaspace` (paths are relative to `infra/`).

- [ ] **Step 4: Update CI workflows**

Look at `.github/workflows/*.yml`. Anywhere a step does `cd module` or paths a `module/Cargo.toml`, replace with `modules/sastaspace`.

```bash
ls .github/workflows/ 2>/dev/null && grep -ln 'module' .github/workflows/*.yml 2>/dev/null
```

Edit each match. Common pattern:
```yaml
# before:
- run: cargo build --manifest-path module/Cargo.toml
# after:
- run: cargo build --manifest-path modules/sastaspace/Cargo.toml
```

- [ ] **Step 5: Update package.json scripts**

```bash
grep -n 'module' package.json apps/*/package.json packages/*/package.json 2>/dev/null
```

Common pattern: a `generate-stdb-bindings` script that does `spacetime generate --project-path module ...`. Replace with `modules/sastaspace`.

- [ ] **Step 6: Build to verify nothing's broken**

```bash
cd modules/sastaspace && cargo build --target wasm32-unknown-unknown --release
```

Expected: clean build, produces `target/wasm32-unknown-unknown/release/sastaspace.wasm` (or the existing crate name — check `Cargo.toml`).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor(modules): rename module/ → modules/sastaspace/

First half of structure-audit H2. Updates Cargo workspace, docker-compose
volume paths, CI workflows, and package.json scripts to the new path.
No behavior change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Rename `game/` → `modules/typewars/`

Same shape as Task 2.

- [ ] **Step 1: git mv**

```bash
git mv game modules/typewars
```

- [ ] **Step 2: Update Cargo workspace**

Edit `Cargo.toml`:
```toml
[workspace]
members = ["modules/sastaspace", "modules/typewars"]
resolver = "2"
```

- [ ] **Step 3: Update docker-compose, CI, package.json**

Repeat Task 2 steps 3–5 for `game` → `modules/typewars`.

- [ ] **Step 4: Build to verify**

```bash
cd modules/typewars && cargo build --target wasm32-unknown-unknown --release
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor(modules): rename game/ → modules/typewars/

Completes structure-audit H2. Sibling layout under modules/. No behavior
change.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Verify STDB module publish still works

Sanity check that the renamed modules can still be published to a local STDB instance.

- [ ] **Step 1: Spin up local STDB**

```bash
cd infra && docker compose up -d spacetime
docker compose logs --tail 30 spacetime
```

Expected: `spacetime` container healthy on `127.0.0.1:3100`. `curl http://127.0.0.1:3100/v1/ping` returns 200.

- [ ] **Step 2: Publish sastaspace module**

```bash
cd modules/sastaspace
spacetime publish --project-path . --server local sastaspace
```

Expected: "Publishing module ... done." If `spacetime` CLI isn't installed, install via `cargo install spacetimedb-cli` (one-time).

- [ ] **Step 3: Publish typewars module**

```bash
cd modules/typewars
spacetime publish --project-path . --server local typewars
```

Expected: same.

- [ ] **Step 4: Smoke test a reducer call**

```bash
spacetime call --server local sastaspace client_connected '[]'
```

Expected: no error. (`client_connected` is one of the existing lifecycle reducers.)

- [ ] **Step 5: No commit needed (verification only)**

If everything works, move on. If anything failed, the rename broke something — diagnose and patch before continuing.

---

## Task 5: Add `workers/` skeleton

A new top-level `workers/` directory with package.json, Dockerfile, and a boot script that registers zero agents (all flags default to false).

**Files:**
- Create: `workers/package.json`, `workers/Dockerfile`, `workers/tsconfig.json`, `workers/.gitignore`
- Create: `workers/src/index.ts`, `workers/src/shared/{stdb.ts,mastra.ts,env.ts}`, `workers/src/agents/{auth-mailer,admin-collector,deck-agent,moderator-agent}.ts` (all stubs)
- Modify: `pnpm-workspace.yaml` (add `workers` to packages)

- [ ] **Step 1: Create the directory**

```bash
mkdir -p workers/src/shared workers/src/agents
```

- [ ] **Step 2: Write `workers/package.json`**

```json
{
  "name": "@sastaspace/workers",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "start": "node --enable-source-maps dist/index.js",
    "build": "tsc -p tsconfig.json",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "tsc -p tsconfig.json --noEmit"
  },
  "dependencies": {
    "@clockworklabs/spacetimedb-sdk": "^1.0.0",
    "@mastra/core": "^0.10.0",
    "@ai-sdk/openai": "^1.0.0",
    "ollama-ai-provider": "^1.0.0",
    "resend": "^4.0.0",
    "dockerode": "^4.0.0",
    "systeminformation": "^5.21.0",
    "jszip": "^3.10.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.4.0",
    "vitest": "^1.5.0",
    "@types/node": "^22.0.0",
    "@types/dockerode": "^3.3.0"
  }
}
```

(Versions are best-effort; `pnpm install` will surface any conflicts and the workstream that first uses each dep can pin precisely.)

- [ ] **Step 3: Write `workers/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "sourceMap": true,
    "declaration": false
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 4: Write `workers/.gitignore`**

```
dist/
node_modules/
*.log
.env.local
```

- [ ] **Step 5: Write `workers/src/shared/env.ts`**

```typescript
import { z } from "zod";

const Env = z.object({
  STDB_URL: z.string().url().default("http://127.0.0.1:3100"),
  STDB_MODULE: z.string().default("sastaspace"),
  STDB_TOKEN: z.string().min(1, "STDB_TOKEN required for owner reducer calls"),

  OLLAMA_URL: z.string().url().default("http://127.0.0.1:11434"),
  OLLAMA_MODEL: z.string().default("gemma3:1b"),
  LOCALAI_URL: z.string().url().default("http://127.0.0.1:8080"),

  RESEND_API_KEY: z.string().optional(),
  RESEND_FROM: z.string().default("hi@sastaspace.com"),

  WORKER_AUTH_MAILER_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_ADMIN_COLLECTOR_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_DECK_AGENT_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),
  WORKER_MODERATOR_AGENT_ENABLED: z.enum(["true", "false"]).default("false").transform(v => v === "true"),

  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

export type Env = z.infer<typeof Env>;
export const env: Env = Env.parse(process.env);
```

- [ ] **Step 6: Write `workers/src/shared/stdb.ts`**

```typescript
// Connection wrapper. Phase 1 workstreams flesh this out with the real
// @clockworklabs/spacetimedb-sdk wiring once the bindings are regenerated
// after their reducers land. For now it's a typed stub so index.ts compiles.

export interface StdbConn {
  callReducer(name: string, ...args: unknown[]): Promise<void>;
  subscribe(query: string, handler: (row: unknown) => void): Promise<void>;
  close(): Promise<void>;
}

export async function connect(_url: string, _module: string, _token: string): Promise<StdbConn> {
  // Phase 1 W1 fills this in. Stubbed to throw so any agent that tries to
  // run before its workstream lands fails loud.
  throw new Error("stdb.connect not implemented yet — Phase 1 W1 deliverable");
}
```

- [ ] **Step 7: Write `workers/src/shared/mastra.ts`**

```typescript
// Mastra setup. Phase 1 W3/W4 flesh this out once we know the exact
// provider package names the version we install settles on.

import { env } from "./env.js";

export const ollamaConfig = {
  baseURL: env.OLLAMA_URL,
  defaultModel: env.OLLAMA_MODEL,
};

export const localaiConfig = {
  baseURL: env.LOCALAI_URL,
};

// Mastra instance is created lazily by each agent that needs it, so agents
// that aren't enabled don't pay the import cost.
```

- [ ] **Step 8: Write empty agent stubs**

Each of `workers/src/agents/{auth-mailer,admin-collector,deck-agent,moderator-agent}.ts` gets:

```typescript
// Stub — fleshed out by Phase 1 W<N>.
import type { StdbConn } from "../shared/stdb.js";

export async function start(_db: StdbConn): Promise<() => Promise<void>> {
  throw new Error("agent not implemented — Phase 1 deliverable");
}
```

(Replace `auth-mailer` etc. in comments. Identical export shape so `index.ts` can call all four uniformly.)

- [ ] **Step 9: Write `workers/src/index.ts`**

```typescript
import { env } from "./shared/env.js";
import { connect } from "./shared/stdb.js";
import { start as startAuthMailer } from "./agents/auth-mailer.js";
import { start as startAdminCollector } from "./agents/admin-collector.js";
import { start as startDeckAgent } from "./agents/deck-agent.js";
import { start as startModeratorAgent } from "./agents/moderator-agent.js";

const log = (level: string, msg: string, extra?: unknown) =>
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, msg, extra }));

async function main(): Promise<void> {
  log("info", "workers booting", {
    auth_mailer: env.WORKER_AUTH_MAILER_ENABLED,
    admin_collector: env.WORKER_ADMIN_COLLECTOR_ENABLED,
    deck_agent: env.WORKER_DECK_AGENT_ENABLED,
    moderator_agent: env.WORKER_MODERATOR_AGENT_ENABLED,
  });

  const enabledAny =
    env.WORKER_AUTH_MAILER_ENABLED ||
    env.WORKER_ADMIN_COLLECTOR_ENABLED ||
    env.WORKER_DECK_AGENT_ENABLED ||
    env.WORKER_MODERATOR_AGENT_ENABLED;

  if (!enabledAny) {
    log("info", "no agents enabled, idling");
    // Stay alive so docker doesn't restart-loop us.
    setInterval(() => {}, 1 << 30);
    return;
  }

  const db = await connect(env.STDB_URL, env.STDB_MODULE, env.STDB_TOKEN);
  const stops: Array<() => Promise<void>> = [];

  if (env.WORKER_AUTH_MAILER_ENABLED) stops.push(await startAuthMailer(db));
  if (env.WORKER_ADMIN_COLLECTOR_ENABLED) stops.push(await startAdminCollector(db));
  if (env.WORKER_DECK_AGENT_ENABLED) stops.push(await startDeckAgent(db));
  if (env.WORKER_MODERATOR_AGENT_ENABLED) stops.push(await startModeratorAgent(db));

  log("info", "all enabled agents started", { count: stops.length });

  const shutdown = async () => {
    log("info", "shutdown requested");
    for (const stop of stops) await stop().catch(e => log("error", "stop failed", String(e)));
    await db.close().catch(e => log("error", "db close failed", String(e)));
    process.exit(0);
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

main().catch(err => {
  log("error", "boot failed", String(err));
  process.exit(1);
});
```

- [ ] **Step 10: Write `workers/Dockerfile`**

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
COPY pnpm-lock.yaml* ./
RUN corepack enable && corepack prepare pnpm@9 --activate && pnpm install --frozen-lockfile
COPY tsconfig.json ./
COPY src ./src
RUN pnpm build

FROM node:22-alpine
WORKDIR /app
RUN apk add --no-cache docker-cli
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
USER node
CMD ["node", "--enable-source-maps", "dist/index.js"]
```

- [ ] **Step 11: Add to `pnpm-workspace.yaml`**

Edit `pnpm-workspace.yaml`. Add `workers` under `packages:`. Final shape (verify against current contents first):

```yaml
packages:
  - "apps/*"
  - "packages/*"
  - "workers"
```

- [ ] **Step 12: Install and type-check**

```bash
pnpm install
pnpm --filter @sastaspace/workers run lint
```

Expected: no TypeScript errors.

- [ ] **Step 13: Verify it boots and idles cleanly**

```bash
cd workers && pnpm dev
```

Expected: prints `{"level":"info","msg":"workers booting",...}` then `{"level":"info","msg":"no agents enabled, idling"}` and stays alive. Ctrl+C exits cleanly.

- [ ] **Step 14: Commit**

```bash
git add workers/ pnpm-workspace.yaml pnpm-lock.yaml
git commit -m "$(cat <<'EOF'
feat(workers): scaffold Mastra-based workers process

Single Node process that registers Mastra agents controlled by per-agent
env feature flags. All flags default off — process boots and idles. Phase 1
workstreams flesh out each agent and the shared STDB connection.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add the `workers` block to docker-compose

The block exists alongside the existing Python services (which keep running). Workers boots with all flags off through Phase 1, so it's a no-op container.

**Files:**
- Modify: `infra/docker-compose.yml`

- [ ] **Step 1: Append the workers service block**

Edit `infra/docker-compose.yml`. After the existing `moderator:` block (or anywhere in the services list), add:

```yaml
  workers:
    build:
      context: ../workers
      dockerfile: Dockerfile
    image: sastaspace-workers:local
    container_name: sastaspace-workers
    restart: unless-stopped
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    pids_limit: 256
    mem_limit: 512m
    user: "1000:1000"
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./deck-out:/app/deck-out:rw
    env_file:
      - ../workers/.env
    environment:
      - STDB_URL=http://127.0.0.1:3100
      - STDB_MODULE=sastaspace
      - OLLAMA_URL=http://127.0.0.1:11434
      - LOCALAI_URL=http://127.0.0.1:8080
      - WORKER_AUTH_MAILER_ENABLED=false
      - WORKER_ADMIN_COLLECTOR_ENABLED=false
      - WORKER_DECK_AGENT_ENABLED=false
      - WORKER_MODERATOR_AGENT_ENABLED=false
    depends_on:
      spacetime:
        condition: service_healthy
```

- [ ] **Step 2: Create the host directories the volumes reference**

```bash
mkdir -p infra/deck-out
touch workers/.env  # so env_file doesn't 404
```

Add `infra/deck-out/` to `infra/.gitignore` (create if missing):
```bash
echo 'deck-out/' >> infra/.gitignore
```

- [ ] **Step 3: Build and start the container locally**

```bash
cd infra && docker compose build workers && docker compose up -d workers
docker compose logs --tail 20 workers
```

Expected: container running, logs show `"workers booting"` and `"no agents enabled, idling"`.

- [ ] **Step 4: Commit**

```bash
git add infra/docker-compose.yml infra/.gitignore workers/.env
git commit -m "$(cat <<'EOF'
feat(infra): wire workers container into compose

All agent flags default off so it idles alongside the existing Python
services without competing. Volume mounts in place for Phase 1
admin-collector (docker.sock) and deck-agent (deck-out).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Install LocalAI on taxila

LocalAI runs as a sibling to Ollama. Self-hosted, GPU-passthrough, idles until Phase 1 W3 deck-agent calls it.

**Files:**
- Create: `infra/localai/models.yaml`, `infra/localai/preload.sh`
- Modify: `infra/docker-compose.yml`

- [ ] **Step 1: Confirm LocalAI image tag**

```bash
docker pull localai/localai:latest-aio-gpu-nvidia-cuda-12  # taxila has 7900 XTX (AMD), so:
docker pull localai/localai:latest-aio-gpu-hipblas
```

(Pick the AMD/ROCm image since taxila is 7900 XTX — confirm GPU vendor with `lspci | grep -i vga` on taxila first. If unsure, the CPU image `localai/localai:latest` works as a fallback to validate the wiring; swap to GPU image once confirmed.)

- [ ] **Step 2: Write `infra/localai/models.yaml`**

```yaml
# LocalAI model registry. Phase 0 ships with one model: facebook/musicgen-small.
# More models can be added by appending; LocalAI hot-loads on first request.

- name: musicgen-small
  backend: musicgen
  parameters:
    model: facebook/musicgen-small
  description: Meta's MusicGen small model — text-to-music, 30 s clips, mono.
```

- [ ] **Step 3: Write `infra/localai/preload.sh`**

```bash
#!/usr/bin/env bash
# Preloads the MusicGen model on first boot. Run inside the LocalAI container
# via an init job in docker-compose, OR run manually after first up.
set -euo pipefail
LOCALAI_URL="${LOCALAI_URL:-http://127.0.0.1:8080}"
echo "Preloading musicgen-small via $LOCALAI_URL ..."
curl -fsSL -X POST "$LOCALAI_URL/models/apply" \
  -H 'Content-Type: application/json' \
  -d '{"id":"musicgen-small","name":"musicgen-small","backend":"musicgen","parameters":{"model":"facebook/musicgen-small"}}' \
  | tee /tmp/localai-preload.json
echo "OK"
```

```bash
chmod +x infra/localai/preload.sh
```

- [ ] **Step 4: Append the localai service block to compose**

Edit `infra/docker-compose.yml`. Add (adjust image tag per Step 1 outcome):

```yaml
  localai:
    image: localai/localai:latest-aio-gpu-hipblas
    container_name: sastaspace-localai
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./localai/models:/models
      - ./localai/models.yaml:/models/models.yaml:ro
    environment:
      - MODELS_PATH=/models
      - DEBUG=false
    devices:
      - /dev/kfd  # AMD GPU
      - /dev/dri  # AMD GPU
    mem_limit: 16g  # MusicGen needs headroom; adjust per taxila's RAM
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8080/readyz"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 60s
```

(The exact device mounts vary by GPU. For NVIDIA: `runtime: nvidia` + remove `devices:`. For AMD ROCm: keep `devices:` as above.)

- [ ] **Step 5: Bring up LocalAI and wait for healthy**

```bash
cd infra && docker compose up -d localai
docker compose ps localai
docker compose logs --tail 30 localai
```

Expected: `localai` container reports healthy within ~60 s. First boot may take longer if downloading the base image.

- [ ] **Step 6: Preload MusicGen**

```bash
infra/localai/preload.sh
```

Expected: JSON response from LocalAI, `/tmp/localai-preload.json` contains `{"uuid": "...", "status": "..."}`. The actual model download happens async; verify with:

```bash
curl -s http://127.0.0.1:8080/models | jq '.data[] | select(.id == "musicgen-small")'
```

Expected: shows the model entry. If still downloading, retry the curl until it appears.

- [ ] **Step 7: Smoke-test a MusicGen call**

```bash
curl -fsSL -X POST http://127.0.0.1:8080/v1/audio/generations \
  -H 'Content-Type: application/json' \
  -d '{"model":"musicgen-small","input":"calm ambient pad, 60bpm, soft piano","duration":4}' \
  -o /tmp/musicgen-test.wav

file /tmp/musicgen-test.wav
```

Expected: `/tmp/musicgen-test.wav` is a RIFF WAV file, ~4 seconds. If the endpoint shape differs (LocalAI version differences), capture the actual shape into `infra/localai/README.md` as a note for Phase 1 W3.

- [ ] **Step 8: Commit**

```bash
git add infra/localai/ infra/docker-compose.yml
git commit -m "$(cat <<'EOF'
feat(infra): add LocalAI sibling to Ollama for self-hosted MusicGen

Phase 0 of stdb-native rewire. Idles until Phase 1 W3 deck-agent uses it.
Preload script installs facebook/musicgen-small on first boot.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Capture the E2E baseline

The Phase 0 acceptance gate is **full E2E suite green**. Before moving to Phase 1, prove the existing suite passes against the renamed-but-otherwise-unchanged stack.

**Files:**
- Modify: `tests/e2e/` if any specs reference `module/` or `game/` paths (most reference apps via URLs, so unlikely)
- Create: `docs/audits/2026-04-26-phase0-e2e-baseline.md` (one-paragraph note + run command + result)

- [ ] **Step 1: Audit E2E specs for hardcoded path references**

```bash
cd tests/e2e
grep -rn -e 'module/' -e 'game/' specs/ helpers/ 2>/dev/null
```

Expected: no hits, or only doc-comment hits. If a real reference exists, update it to `modules/sastaspace` or `modules/typewars`.

- [ ] **Step 2: Run the full E2E suite locally against dev compose**

```bash
cd infra && docker compose up -d  # bring up everything, including the still-running Python services
cd ../tests/e2e && pnpm install && pnpm test
```

Expected: green. If anything fails, this is a regression from Tasks 2–6 — diagnose before continuing. Common cause: a path miss from Task 1 audit.

- [ ] **Step 3: Capture the baseline result**

Write `docs/audits/2026-04-26-phase0-e2e-baseline.md`:

```markdown
# Phase 0 E2E Baseline

**Date:** 2026-04-26
**Commit:** <git rev-parse HEAD output>

Ran the full Playwright suite against dev compose after the SpacetimeDB-native
rewire's Phase 0 changes (module rename, workers skeleton, LocalAI install).
Stack at this point: spacetime + ollama + localai + workers (idle) + 4 Python
services (still active) + 4 nginx static apps.

## Result
PASS — N specs, M assertions, T seconds total. (Fill in with actual numbers.)

## Specs covered
- (paste output of `pnpm test --list` or summarize)

This baseline is the regression gate Phase 1+ measures against.
```

- [ ] **Step 4: Commit the baseline doc**

```bash
git add docs/audits/2026-04-26-phase0-e2e-baseline.md
git commit -m "$(cat <<'EOF'
docs(audits): Phase 0 E2E baseline captured

Full Playwright suite green after module rename + workers skeleton +
LocalAI install. Establishes the regression gate Phase 1 work measures
against.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Refresh the knowledge graph

The repo has a graphify skill rule: "After modifying code files in this session, run `graphify update .` to keep the graph current."

- [ ] **Step 1: Update the graph**

```bash
cd /Users/mkhare/Development/sastaspace
graphify update .
```

Expected: graph rebuilds incrementally. AST-only mode means no API cost.

- [ ] **Step 2: Spot-check the result**

```bash
head -60 graphify-out/GRAPH_REPORT.md
```

Expected: the community structure should now reference `modules/sastaspace` and `modules/typewars` instead of `module` and `game`.

- [ ] **Step 3: Commit the refreshed graph**

```bash
git add graphify-out/
git commit -m "$(cat <<'EOF'
chore(graphify): refresh after Phase 0 path changes

Reflects modules/ rename and new workers/ tree. AST-only update, no API
cost.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 0 acceptance checklist

Before Phase 1 dispatches, verify all of these:

- [ ] `modules/sastaspace/` and `modules/typewars/` exist; `module/` and `game/` do not
- [ ] `cd modules/sastaspace && cargo build --target wasm32-unknown-unknown --release` succeeds
- [ ] `cd modules/typewars && cargo build --target wasm32-unknown-unknown --release` succeeds
- [ ] `pnpm --filter @sastaspace/workers run lint` succeeds
- [ ] `cd infra && docker compose up -d` starts all containers including `workers` (idle) and `localai` (healthy)
- [ ] `infra/localai/preload.sh` succeeds; `/tmp/musicgen-test.wav` is a valid WAV file
- [ ] `cd tests/e2e && pnpm test` is fully green
- [ ] `docs/audits/2026-04-26-phase0-e2e-baseline.md` committed
- [ ] `graphify-out/` refreshed and committed
- [ ] No Python service was modified or removed — `services/auth/`, `services/admin-api/`, `services/deck/`, `infra/agents/moderator/` all still on disk and still build

When all are checked, Phase 0 is done. Master plan's next action: draft Phase 1 W1–W4 plan files and dispatch parallel subagents.

---

## Self-review (writing-plans hygiene)

**Spec coverage check:** Phase 0 should produce: (a) module rename, (b) workers skeleton, (c) LocalAI install, (d) E2E baseline. Tasks 2–4 cover (a). Tasks 5–6 cover (b). Task 7 covers (c). Task 8 covers (d). Task 9 keeps the knowledge graph honest. Task 1 is prep. ✅ no gaps.

**Placeholder scan:** No "TBD" or "TODO" survives. Image tag in Task 7 has a documented fork (NVIDIA vs AMD) — acceptable because we tell the engineer how to choose. The Mastra config in Task 5 Step 7 is intentionally minimal because Phase 1 W3/W4 flesh it out — a comment in the file makes that explicit. ✅

**Type/signature consistency:** `StdbConn` interface in `shared/stdb.ts` matches the calls in `index.ts` (callReducer, subscribe, close). Agent `start(db)` signature consistent across all four stub files. Env var names match between `env.ts`, compose, and the spec. ✅

**Sequencing:** Task 4 (module publish smoke test) comes after Task 3 (game rename) so both modules are tested in their new homes. Task 6 (compose wiring) comes after Task 5 (workers code) because the compose block builds from the new directory. Task 7 is independent of Tasks 5–6 (LocalAI doesn't need workers) but must come before Task 8 (LocalAI needs to be up for the baseline E2E to be representative of post-Phase-0 state). ✅
