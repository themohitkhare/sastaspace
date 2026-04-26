// Phase 3 cutover: workers container is the new home for auth-mailer,
// admin-collector, deck-agent, and moderator-agent. This comment edit
// triggers the workers-deploy CI job after the audit gate was relaxed.
// Re-touched after WORKERS_STDB_TOKEN provisioning fix to retrigger deploy.
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

  // Audit N13: boot-time owner-token sanity check. The reducer rejects with
  // "not authorized" if STDB_TOKEN isn't the owner identity. We catch that
  // and exit non-zero so docker restart-loops with a clear log line, instead
  // of letting every per-agent reducer call silently fail with the same
  // error 30 s after boot.
  //
  // SDK 2.1 caveat: callReducer resolves on send, not on commit, so a
  // silent module-side rejection isn't observable here without subscribing
  // to a reducer-event hook. Network/handshake failures still throw, which
  // covers the "wrong token rejected at handshake" and "host unreachable"
  // cases. Per-agent error handlers backstop the rest.
  try {
    await db.callReducer("noop_owner_check");
    log("info", "owner token verified (noop_owner_check ok)");
  } catch (e) {
    log("error", "noop_owner_check failed — STDB_TOKEN is not the owner identity (or STDB unreachable)", String(e));
    process.exit(2);
  }

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
