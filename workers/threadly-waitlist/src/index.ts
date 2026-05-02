/**
 * Threadly waitlist worker — captures emails into KV with dedup + light rate
 * limiting. POST /join { email, source } → 200 { ok: true, position }.
 * GET /count → public count of signups.
 */

interface Env {
  WAITLIST: KVNamespace;
  ALLOWED_ORIGINS?: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const COUNTER_KEY = "__count__";
const RATE_PREFIX = "rate:";
const RATE_WINDOW_SEC = 60;
const RATE_LIMIT = 5;

function corsHeaders(origin: string | null, allowed: string | undefined): Record<string, string> {
  const allowList = (allowed ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  const allowOrigin =
    allowList.length === 0 ? "*" : allowList.includes(origin ?? "") ? origin! : allowList[0];
  return {
    "access-control-allow-origin": allowOrigin,
    "access-control-allow-methods": "POST, GET, OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
  };
}

function json(body: unknown, init: ResponseInit & { cors: Record<string, string> }) {
  const { cors, ...rest } = init;
  return new Response(JSON.stringify(body), {
    ...rest,
    headers: { "content-type": "application/json", ...cors, ...(rest.headers ?? {}) },
  });
}

async function checkRate(kv: KVNamespace, ip: string): Promise<boolean> {
  const key = RATE_PREFIX + ip;
  const current = parseInt((await kv.get(key)) ?? "0", 10);
  if (current >= RATE_LIMIT) return false;
  await kv.put(key, String(current + 1), { expirationTtl: RATE_WINDOW_SEC });
  return true;
}

async function bumpCount(kv: KVNamespace): Promise<number> {
  const cur = parseInt((await kv.get(COUNTER_KEY)) ?? "0", 10);
  const next = cur + 1;
  await kv.put(COUNTER_KEY, String(next));
  return next;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const cors = corsHeaders(req.headers.get("origin"), env.ALLOWED_ORIGINS);

    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    if (req.method === "GET" && url.pathname === "/count") {
      const count = parseInt((await env.WAITLIST.get(COUNTER_KEY)) ?? "0", 10);
      return json({ count }, { cors });
    }

    if (req.method === "POST" && url.pathname === "/join") {
      const ip = req.headers.get("cf-connecting-ip") ?? "unknown";
      if (!(await checkRate(env.WAITLIST, ip))) {
        return json({ ok: false, error: "rate_limited" }, { status: 429, cors });
      }

      let body: { email?: string; source?: string };
      try {
        body = await req.json();
      } catch {
        return json({ ok: false, error: "invalid_json" }, { status: 400, cors });
      }

      const email = (body.email ?? "").trim().toLowerCase();
      if (!EMAIL_RE.test(email)) {
        return json({ ok: false, error: "invalid_email" }, { status: 400, cors });
      }

      const key = "email:" + email;
      const existing = await env.WAITLIST.get(key);
      if (existing) {
        return json({ ok: true, duplicate: true }, { cors });
      }

      const record = {
        email,
        source: (body.source ?? "").slice(0, 80),
        ip,
        userAgent: req.headers.get("user-agent")?.slice(0, 200) ?? "",
        joinedAt: new Date().toISOString(),
      };
      await env.WAITLIST.put(key, JSON.stringify(record));
      const position = await bumpCount(env.WAITLIST);

      return json({ ok: true, position }, { cors });
    }

    return json({ ok: false, error: "not_found" }, { status: 404, cors });
  },
};
