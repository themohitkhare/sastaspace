import { describe, it, expect } from "vitest"
import type { RedesignState } from "@/hooks/use-redesign"

describe("RedesignState type", () => {
  it("progress state has siteColors and siteTitle", () => {
    const s: RedesignState = {
      status: "progress",
      currentStep: "crawling",
      domain: "example.com",
      steps: [],
      tier: "free",
      jobId: "abc",
      siteColors: ["#ff0000"],
      siteTitle: "Example",
      retryCount: 0,
      jobCreatedAt: "",
    }
    expect(s.status).toBe("progress")
    if (s.status === "progress") {
      expect(s.siteColors).toEqual(["#ff0000"])
      expect(s.siteTitle).toBe("Example")
    }
  })

  it("error state can carry resumeJobId for network-failure resume", () => {
    const s: RedesignState = {
      status: "error",
      message: "Having trouble connecting.",
      url: "https://example.com",
      resumeJobId: "job-123",
    }
    if (s.status === "error") {
      expect(s.resumeJobId).toBe("job-123")
    }
  })
})
