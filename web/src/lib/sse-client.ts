// web/src/lib/sse-client.ts

export type SSEEvent = {
  event: string
  data: Record<string, unknown>
}

/** Submit a redesign request. Returns job_id (Redis path) or throws. */
export async function submitRedesign(
  url: string,
  tier: "free" | "standard" | "premium" = "free",
  signal?: AbortSignal
): Promise<string> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  const resp = await fetch(`${backendUrl}/redesign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, tier }),
    signal,
  })
  if (!resp.ok) throw new Error(`Redesign request failed: ${resp.status}`)
  const data = (await resp.json()) as { job_id?: string }
  if (data.job_id) return data.job_id
  throw new Error("No job_id returned from server")
}

/** Stream status events for a job. Reconnectable. */
export async function* streamJobStatus(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  const resp = await fetch(`${backendUrl}/jobs/${jobId}/stream`, { signal })
  if (!resp.ok || !resp.body) throw new Error(`Stream failed: ${resp.status}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let currentEvent = "message"

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() ?? ""

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        try {
          const data = JSON.parse(line.slice(5).trim()) as Record<string, unknown>
          yield { event: currentEvent, data }
          currentEvent = "message"
        } catch {
          // skip malformed
        }
      }
    }
  }
}
