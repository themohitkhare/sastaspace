import { describe, it, expect } from "vitest"
import type { ActivityItem, DiscoveryItem } from "@/hooks/use-redesign"

describe("use-redesign types", () => {
  it("ActivityItem has id, agent, message, timestamp", () => {
    const item: ActivityItem = {
      id: "1",
      agent: "design_strategist",
      message: "Crafting your design direction",
      timestamp: Date.now(),
    }
    expect(item.agent).toBe("design_strategist")
  })

  it("DiscoveryItem has label and value", () => {
    const item: DiscoveryItem = { label: "Colors", value: "4 detected" }
    expect(item.label).toBe("Colors")
  })
})
