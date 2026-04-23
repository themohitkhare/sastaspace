import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("concatenates class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("filters falsy values", () => {
    expect(cn("a", false && "x", null, undefined, "b")).toBe("a b");
  });

  it("merges tailwind conflicts via tailwind-merge (last wins)", () => {
    expect(cn("p-4", "p-8")).toContain("p-8");
    expect(cn("p-4", "p-8")).not.toContain("p-4");
  });
});
