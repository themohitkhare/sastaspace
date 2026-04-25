import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";

let emitter: ((n: number) => void) | null = null;
vi.mock("@/lib/spacetime", () => ({
  STDB_URI: "wss://test",
  STDB_MODULE: "test",
  subscribePresence: (fn: (n: number) => void) => {
    emitter = fn;
    fn(0);
    return () => {
      emitter = null;
    };
  },
}));

import { PresencePill } from "@/components/PresencePill";

afterEach(() => {
  emitter = null;
});

describe("PresencePill", () => {
  it("renders nothing when count is zero", () => {
    const { container } = render(<PresencePill />);
    expect(container.textContent).toBe("");
  });

  it("renders singular form when one person is present", () => {
    render(<PresencePill />);
    act(() => emitter!(1));
    expect(screen.getByText("1 in the lab")).toBeInTheDocument();
  });

  it("renders plural form for >1", () => {
    render(<PresencePill />);
    act(() => emitter!(7));
    expect(screen.getByText("7 in the lab")).toBeInTheDocument();
  });

  it("hides again when count drops back to zero", () => {
    const { container } = render(<PresencePill />);
    act(() => emitter!(3));
    expect(screen.getByText("3 in the lab")).toBeInTheDocument();
    act(() => emitter!(0));
    expect(container.textContent).toBe("");
  });
});
