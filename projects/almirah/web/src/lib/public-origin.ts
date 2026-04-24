// Derive the public-facing origin a request was received on. Inside the pod
// the Next.js server binds to 0.0.0.0:3000 — so `new URL(request.url).origin`
// returns "http://0.0.0.0:3000" which is useless for building a redirect the
// browser can follow. nginx-ingress forwards the real host via X-Forwarded-*;
// the scheme is tricky because the Cloudflare-tunnel-to-ingress hop is HTTP,
// so X-Forwarded-Proto says "http" even though the browser hit HTTPS. We
// force https for any non-loopback host to avoid that footgun.
export function publicOrigin(request: Request): string {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (!host) {
    return new URL(request.url).origin;
  }
  const bareHost = host.split(":")[0];
  const isLocal =
    bareHost === "localhost" ||
    bareHost === "127.0.0.1" ||
    bareHost === "0.0.0.0" ||
    bareHost.endsWith(".localhost");
  const proto = isLocal
    ? request.headers.get("x-forwarded-proto") ?? "http"
    : "https";
  return `${proto}://${host}`;
}
