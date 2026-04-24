// Validates a `next=` redirect parameter. Returns either a same-origin path
// or an absolute HTTPS URL on a *.sastaspace.com subdomain. Anything else
// collapses to "/" — this prevents open-redirect + protocol-handler attacks.

const ALLOWED_APEX = "sastaspace.com";

// `origin` is accepted (but unused) to keep the signature future-compatible if
// we ever want to treat same-origin paths differently from cross-origin ones.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function getSafeNext(next: string | null, origin: string): string {
  if (!next) return "/";

  // Block scheme-relative //host and //\host variants, and weird leading \.
  if (next.startsWith("/") && (next[1] === "/" || next[1] === "\\")) return "/";

  // Relative path — accept only if it starts with a single "/".
  if (next.startsWith("/")) return next;

  // Absolute URL — parse and validate host + protocol.
  let url: URL;
  try {
    url = new URL(next);
  } catch {
    return "/";
  }

  if (url.protocol !== "https:") return "/";
  if (url.username || url.password) return "/";

  const host = url.hostname.toLowerCase();
  const isApex = host === ALLOWED_APEX;
  const isSubdomain = host.endsWith("." + ALLOWED_APEX);
  if (!isApex && !isSubdomain) return "/";

  return url.toString();
}
