export type SSEEvent = {
  event: string;
  data: Record<string, unknown>;
};

export async function* streamRedesign(
  url: string,
  apiBase: string = "http://localhost:8080",
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${apiBase}/redesign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      (errorBody as Record<string, string>).error ||
        (errorBody as Record<string, string>).detail ||
        `HTTP ${response.status}`
    );
  }

  const reader = response
    .body!.pipeThrough(new TextDecoderStream())
    .getReader();

  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += value;

      const parts = buffer.split("\n\n");
      // Keep the last part as buffer (may be incomplete)
      buffer = parts.pop()!;

      for (const block of parts) {
        if (!block.trim()) continue;

        let eventName = "message";
        let dataStr = "";

        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataStr = line.slice(5).trim();
          }
        }

        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr) as Record<string, unknown>;
          yield { event: eventName, data };
        } catch {
          // Skip malformed events silently
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
