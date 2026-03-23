// web/src/lib/sse-client.ts

export type JobStatus = {
  id: string
  status: "queued" | "crawling" | "discovering" | "downloading" | "analyzing" | "redesigning" | "deploying" | "done" | "failed"
  progress: number
  message: string
  subdomain?: string
  error?: string
  site_colors?: string[]
  site_title?: string
  created_at?: string
  pages_crawled?: number
  assets_count?: number
}

/** Submit a redesign request. Returns job_id or throws. */
export async function submitRedesign(
  url: string,
  tier: "free" | "premium" = "free",
  modelProvider: "claude" | "gemini" = "claude",
  signal?: AbortSignal,
  prompt: string = "",
): Promise<string> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  const body: Record<string, string> = { url, tier, model_provider: modelProvider }
  if (prompt) body.prompt = prompt
  const resp = await fetch(`${backendUrl}/redesign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  })
  if (!resp.ok) throw new Error(`Redesign request failed: ${resp.status}`)
  const data = (await resp.json()) as { job_id?: string }
  if (data.job_id) return data.job_id
  throw new Error("No job_id returned from server")
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Poll GET /jobs/{id} every 3s (1s when deploying).
 * Silently retries on network errors; throws "POLL_FAILED" after 5 consecutive failures.
 * Generator stops when status is "done" or "failed".
 */
export async function* pollJobStatus(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<JobStatus> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  let consecutiveFailures = 0
  let lastStatus: string = "queued"

  while (true) {
    if (signal?.aborted) return

    try {
      const resp = await fetch(`${backendUrl}/jobs/${jobId}`, { signal })
      if (signal?.aborted) return

      if (resp.ok) {
        consecutiveFailures = 0
        const job = (await resp.json()) as JobStatus
        lastStatus = job.status
        yield job
        if (job.status === "done" || job.status === "failed") return
      } else {
        consecutiveFailures++
      }
    } catch {
      if (signal?.aborted) return
      consecutiveFailures++
    }

    if (consecutiveFailures >= 5) {
      throw new Error("POLL_FAILED")
    }

    const intervalMs = lastStatus === "deploying" ? 1000 : 3000
    await sleep(intervalMs)
  }
}
