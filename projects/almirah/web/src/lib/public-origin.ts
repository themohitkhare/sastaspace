// Derive the public-facing origin a request was received on. Inside the pod
// the Next.js server binds to 0.0.0.0:3000 — so `new URL(request.url).origin`
// returns "http://0.0.0.0:3000" which is useless for building a redirect the
// browser can follow. nginx-ingress forwards the real host/scheme via
// X-Forwarded-* headers; we prefer those.
export function publicOrigin(request: Request): string {
  const proto = request.headers.get("x-forwarded-proto");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (host) {
    return `${proto ?? "https"}://${host}`;
  }
  // Last-resort fallback: parse the request URL. Only reachable in dev where
  // there's no ingress in front.
  return new URL(request.url).origin;
}
