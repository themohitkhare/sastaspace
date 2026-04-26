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
