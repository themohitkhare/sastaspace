// web/src/app/[subdomain]/preview/route.ts
import type { NextRequest } from "next/server";

// Server-only: use internal k8s service URL to avoid roundtrip through public internet.
// Set BACKEND_INTERNAL_URL=http://localhost:8080 in local dev.
const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8080";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ subdomain: string }> },
) {
  const { subdomain } = await params;

  let res: Response;
  try {
    res = await fetch(`${BACKEND}/${subdomain}/`, { cache: "no-store" });
  } catch {
    return new Response("Preview unavailable", { status: 502 });
  }

  if (!res.ok) {
    return new Response("Not found", { status: res.status });
  }

  const html = await res.text();
  return new Response(html, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
