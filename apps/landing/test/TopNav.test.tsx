import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockPathname = vi.fn(() => "/");
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));
vi.mock("@/lib/spacetime", () => ({
  STDB_URI: "wss://test",
  STDB_MODULE: "test",
  subscribePresence: () => () => {},
}));

import { TopNav } from "@/components/TopNav";

describe("TopNav", () => {
  it("renders all primary nav items", () => {
    render(<TopNav />);
    expect(screen.getByText("the lab")).toBeInTheDocument();
    expect(screen.getByText("projects")).toBeInTheDocument();
    expect(screen.getByText("notes")).toBeInTheDocument();
    expect(screen.getByText("about")).toBeInTheDocument();
  });

  it("notes points to the notes subdomain (external)", () => {
    render(<TopNav />);
    expect(screen.getByText("notes").closest("a")?.getAttribute("href")).toBe(
      "https://notes.sastaspace.com",
    );
  });

  it("brand mark links to home", () => {
    render(<TopNav />);
    expect(
      screen.getByLabelText(/sastaspace home/i).getAttribute("href"),
    ).toBe("/");
  });

  it("marks current page with aria-current=page", () => {
    mockPathname.mockReturnValueOnce("/lab");
    render(<TopNav />);
    expect(screen.getByText("the lab").closest("a")?.getAttribute("aria-current")).toBe("page");
    expect(screen.getByText("projects").closest("a")?.getAttribute("aria-current")).toBeNull();
  });

  it("treats nested routes as still active", () => {
    mockPathname.mockReturnValueOnce("/projects/some-deep-route");
    render(<TopNav />);
    expect(
      screen.getByText("projects").closest("a")?.getAttribute("aria-current"),
    ).toBe("page");
  });
});
