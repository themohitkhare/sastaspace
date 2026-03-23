const KNOWN_EVENTS = new Set([
  "redesign_start",
  "redesign_complete",
  "redesign_error",
  "contact_form_open",
  "contact_form_submit",
  "result_page_view",
  "page_view",
  "cta_click",
]);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { event, data } = body;

    // Validate event type — silently accept unknown events but don't log them
    if (!event || typeof event !== "string") {
      return Response.json({ ok: true });
    }

    const isKnown = KNOWN_EVENTS.has(event);

    // Structured log for Loki/Grafana ingestion
    const logEntry = {
      event,
      known: isKnown,
      data: data ?? null,
      timestamp: new Date().toISOString(),
      userAgent: request.headers.get("user-agent") ?? "unknown",
      ip:
        request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
        request.headers.get("x-real-ip") ??
        "unknown",
    };

    // Always log structured events — Promtail picks these up for Loki
    console.log(JSON.stringify(logEntry));

    return Response.json({ ok: true });
  } catch {
    // Always return 200 — analytics should never surface errors to the client
    return Response.json({ ok: true });
  }
}
