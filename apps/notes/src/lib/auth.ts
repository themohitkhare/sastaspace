// Client-side auth state for the notes app.
//
// Sign-in flow:
//   1. User enters email in the AuthMenu modal
//   2. POST https://auth.sastaspace.com/auth/request {email}
//   3. User clicks magic link → routed to /auth/verify on auth.sastaspace.com
//   4. auth.sastaspace.com mints an stdb identity + JWT, redirects to
//      https://notes.sastaspace.com/auth/callback#token=...&email=...
//   5. /auth/callback parses fragment, calls saveSession(), redirects home
//
// On every page load, getSession() pulls the JWT + email from localStorage
// (if present). That JWT is the stdb token for the user's Identity, used
// to call submit_user_comment as a signed-in user.

const STORAGE_KEY = "sastaspace.auth.v1";
const AUTH_BASE =
  process.env.NEXT_PUBLIC_AUTH_BASE ?? "https://auth.sastaspace.com";

// Phase 2 F1: when true, requestMagicLink calls the STDB reducer instead of
// POSTing to the legacy FastAPI auth service. Default is false so the legacy
// path keeps working until the Phase 3 cutover flips it in production.
const USE_STDB_AUTH = process.env.NEXT_PUBLIC_USE_STDB_AUTH === "true";

export type Session = {
  token: string;
  email: string;
  display_name: string;
  /** ms since epoch when the session was created (for stale-token expiry hints) */
  saved_at: number;
};

type Listener = (session: Session | null) => void;

const listeners = new Set<Listener>();

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    if (
      typeof parsed.token === "string" &&
      typeof parsed.email === "string" &&
      typeof parsed.display_name === "string"
    ) {
      return {
        token: parsed.token,
        email: parsed.email,
        display_name: parsed.display_name,
        saved_at: typeof parsed.saved_at === "number" ? parsed.saved_at : Date.now(),
      };
    }
  } catch {
    // fall through
  }
  return null;
}

export function saveSession(token: string, email: string): Session {
  const session: Session = {
    token,
    email,
    display_name: email.split("@")[0] ?? email,
    saved_at: Date.now(),
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }
  notify(session);
  return session;
}

export function clearSession(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  notify(null);
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  fn(getSession());
  return () => {
    listeners.delete(fn);
  };
}

function notify(s: Session | null) {
  for (const fn of listeners) fn(s);
}

/** Ask the auth service to email the user a magic link. Throws on HTTP error.
 *
 *  When NEXT_PUBLIC_USE_STDB_AUTH=true, this dispatches to the STDB
 *  request_magic_link reducer instead. Dynamic import keeps the bindings
 *  out of the legacy bundle.
 */
export async function requestMagicLink(email: string): Promise<void> {
  if (USE_STDB_AUTH) {
    const { requestMagicLinkViaStdb } = await import("./stdbAuth");
    await requestMagicLinkViaStdb(email);
    return;
  }
  // Legacy FastAPI path — unchanged.
  const r = await fetch(`${AUTH_BASE}/auth/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!r.ok) {
    let detail = "";
    try {
      const data = await r.json();
      detail = typeof data.detail === "string" ? data.detail : "";
    } catch {
      /* ignore */
    }
    throw new Error(detail || `request failed (HTTP ${r.status})`);
  }
}

/**
 * Persist a session built by the STDB-native verify flow. Unlike saveSession,
 * this trusts the caller's display_name and (optional) identity rather than
 * deriving from the email. The legacy Session shape is preserved so existing
 * readers (e.g. the FastAPI callback page) keep working byte-identically.
 *
 * Identity is stored alongside the session for future use (e.g. profile
 * screens) but is intentionally not part of the typed Session shape — readers
 * that need it can re-parse the JSON blob themselves.
 */
export function saveFullSession(args: {
  token: string;
  email: string;
  display_name: string;
  identity?: string;
}): Session {
  const session: Session = {
    token: args.token,
    email: args.email,
    display_name: args.display_name,
    saved_at: Date.now(),
  };
  if (typeof window !== "undefined") {
    const payload = args.identity
      ? { ...session, identity: args.identity }
      : session;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }
  notify(session);
  return session;
}
