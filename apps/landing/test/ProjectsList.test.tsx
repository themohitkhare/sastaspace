import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";

type Project = {
  slug: string;
  title: string;
  blurb: string;
  status: string;
  tags: string[];
  url: string;
};

let emitter: ((rows: readonly Project[]) => void) | null = null;
vi.mock("@/lib/projects", () => ({
  subscribeProjects: (fn: (rows: readonly Project[]) => void) => {
    emitter = fn;
    fn([]);
    return () => {
      emitter = null;
    };
  },
}));

import { ProjectsList } from "@/components/ProjectsList";

afterEach(() => {
  emitter = null;
});

const sampleRows: Project[] = [
  {
    slug: "notes",
    title: "Notes",
    blurb: "Plain-text notes.",
    status: "live",
    tags: ["next"],
    url: "https://notes.sastaspace.com",
  },
  {
    slug: "echo",
    title: "Echo",
    blurb: "URL → podcast feed.",
    status: "wip",
    tags: ["go"],
    url: "https://echo.sastaspace.com",
  },
];

describe("ProjectsList", () => {
  it("renders the brand-correct empty state when no projects exist", () => {
    render(<ProjectsList />);
    expect(
      screen.getByText("The workshop's quiet today. Come back soon."),
    ).toBeInTheDocument();
  });

  it("renders cards when rows arrive", () => {
    render(<ProjectsList />);
    act(() => emitter!(sampleRows));
    expect(screen.getByText("Notes")).toBeInTheDocument();
    expect(screen.getByText("Echo")).toBeInTheDocument();
    expect(screen.getByText("notes.sastaspace.com")).toBeInTheDocument();
    // chip text
    expect(screen.getByText("live")).toBeInTheDocument();
    expect(screen.getByText("wip")).toBeInTheDocument();
  });

  it("links each card to its url", () => {
    render(<ProjectsList />);
    act(() => emitter!(sampleRows));
    const link = screen
      .getByText("Notes")
      .closest("a");
    expect(link?.getAttribute("href")).toBe("https://notes.sastaspace.com");
  });

  it("falls back to empty state when rows clear", () => {
    render(<ProjectsList />);
    act(() => emitter!(sampleRows));
    expect(screen.getByText("Notes")).toBeInTheDocument();
    act(() => emitter!([]));
    expect(
      screen.getByText("The workshop's quiet today. Come back soon."),
    ).toBeInTheDocument();
  });
});
