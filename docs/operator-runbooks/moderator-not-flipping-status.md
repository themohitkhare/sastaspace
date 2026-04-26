# Operator runbook — moderator-agent not flipping comment status

**Symptom:** e2e specs `moderator.spec.ts:benign comment → status='approved'` and `moderator.spec.ts:injection-attempt → status='flagged'` time out with `pollUntil last=null` after 10 s. Comments inserted via `submit_user_comment` stay at `status='pending'` forever.

**Last verified:** 2026-04-27 — `register_owner_self` reducer + workers-deploy successful, but moderator never flips status.

## Pre-flight

Confirm the chain DOWN to the moderator-agent is healthy:

```bash
ssh mkhare@192.168.0.37
cd /home/mkhare/sastaspace/infra
docker compose ps workers ollama spacetime
```

All three should show `Up (healthy)`.

## Diagnostic in priority order

### Step 1 — moderator-agent reachability

```bash
docker logs sastaspace-workers --tail 100 | grep -i moderator
```

Look for these lines from `workers/src/agents/moderator-agent.ts`:

| Line                                                  | Means                                                                   |
|-------------------------------------------------------|-------------------------------------------------------------------------|
| `moderator-agent started` + model name                | Agent booted, subscription armed                                        |
| `injection detected … reply=ATTACK`                   | Detector fired, classified as injection — should call `setStatus(flagged)` |
| `comment approved …`                                  | Classifier ran, returned SAFE                                           |
| `injection detector threw → fail-closed`              | Ollama unreachable / errored — should still call `setStatus(flagged, classifier-error)` |
| `set_comment_status_with_reason failed`               | Reducer call rejected — copy the error message                          |

If `moderator-agent started` is missing → workers boot didn't reach it. Check `WORKER_MODERATOR_AGENT_ENABLED=true` in `infra/docker-compose.yml`. Restart workers:

```bash
docker compose up -d --force-recreate workers
```

If you see classifications happening but status not flipping → the reducer call is the issue (jump to Step 3).

### Step 2 — Ollama reachability from workers container

`workers` runs with `network_mode: host` so localhost = host. Ollama binds 127.0.0.1:11434.

```bash
docker exec sastaspace-workers wget -qO- --timeout=4 http://127.0.0.1:11434/api/tags || echo "ollama unreachable from workers"
```

Should return JSON list of models. If unreachable, `sastaspace-ollama` may be down or bound to a different interface. Check:

```bash
docker compose ps ollama
docker logs sastaspace-ollama --tail 30
```

### Step 3 — STDB reducer reachability

Test the reducer directly with the workers' STDB token:

```bash
SPACETIME_TOKEN=$(grep ^STDB_TOKEN= /home/mkhare/sastaspace/workers/.env | cut -d= -f2)
COMMENT_ID=8567   # use an actual id from a recent failed e2e run

curl -sS -X POST \
  -H "Authorization: Bearer $SPACETIME_TOKEN" \
  -H "Content-Type: application/json" \
  --data "[{\"id\":$COMMENT_ID,\"status\":\"approved\",\"reason\":\"manual-test\"}]" \
  -w '\n%{http_code}\n' \
  https://stdb.sastaspace.com/v1/database/sastaspace/call/set_comment_status_with_reason
```

- HTTP 200/204 → reducer accepts owner JWT; the workers copy in `.env` matches `OWNER_HEX`. Status should flip on prod.
- HTTP 401/403 → workers `.env` has stale or non-owner token. See `docs/operator-runbooks/localai-musicgen-swap.md` (similar provisioning pattern) for `gh secret list` + redeploy via dispatch.
- HTTP 530 with `not authorized` → JWT decoded but identity ≠ OWNER_HEX. Same fix as 401.
- HTTP 530 with `invalid status` or similar → reducer call shape mismatch. Should not happen post `a5bd0993` SDK 2.1 args fix.

### Step 4 — STDB subscription firing

If logs show `moderator-agent started` but no classifications when you insert test rows:

```bash
SPACETIME_TOKEN=$(grep ^STDB_TOKEN= /home/mkhare/sastaspace/workers/.env | cut -d= -f2)

# Count pending rows the moderator should be processing.
curl -sS -X POST -H "Content-Type: text/plain" \
  -H "Authorization: Bearer $SPACETIME_TOKEN" \
  --data "SELECT COUNT(*) FROM comment WHERE status = 'pending'" \
  https://stdb.sastaspace.com/v1/database/sastaspace/sql
```

If pending count > 0 but moderator-agent isn't picking them up, the subscription `SELECT * FROM comment WHERE status = 'pending'` may not be firing onInsert for owner-issued submit_user_comment rows.

Check the SDK lifecycle in `workers/src/agents/moderator-agent.ts:267-278` — `conn.db.comment.onInsert(...)` and the initial `for ... of conn.db.comment.iter()` drain.

### Step 5 — fail-closed path

The moderator's design has every error path call `setStatus(flagged, ...)`. If status NEVER changes for any comment, the agent is failing BEFORE reaching `setStatus`. Most likely Step 1 didn't show `moderator-agent started`, or workers crashed silently after boot.

## Fix paths by diagnosis

| Diagnosis                                  | Fix                                                                                                         |
|--------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `WORKER_MODERATOR_AGENT_ENABLED` not true  | Edit `infra/docker-compose.yml`, push. CI's workers-deploy will recreate.                                  |
| Workers `.env` token wrong                 | `gh secret set WORKERS_STDB_TOKEN` with fresh JWT, dispatch deploy, wait for workers-deploy.                |
| Ollama down                                | `docker compose up -d ollama`. Wait 30 s for model load. Re-run e2e.                                       |
| Subscription not firing onInsert           | Check STDB SDK version. Re-publish module: dispatch deploy. Workers reconnect on restart.                  |
| Reducer rejects with "not authorized"      | Workers `.env` STDB_TOKEN is not owner identity. Same fix as token-wrong.                                  |

## Once fixed

Trigger a fresh e2e run:

```bash
gh workflow run deploy.yml --ref main
gh run watch $(gh run list --workflow deploy.yml --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId')
```

E2E should drop from 84 passed / 12 failed → 96 passed / 0 failed.

## Tracked in

- Audit: `docs/audits/2026-04-26-audit-consolidated.md` — moderator e2e plateau
- Runbook companion: `docs/operator-runbooks/localai-musicgen-swap.md` (deck audio)
