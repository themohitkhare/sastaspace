export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Log in development for debugging
    if (process.env.NODE_ENV === "development") {
      console.log("[analytics]", body.event, body.data ?? "");
    }

    // TODO: persist to a real analytics store (e.g. Tinybird, Plausible, or Postgres)
    // For now this is a fire-and-forget sink so the client sendBeacon always succeeds.

    return Response.json({ ok: true });
  } catch {
    // Always return 200 — analytics should never surface errors to the client
    return Response.json({ ok: true });
  }
}
