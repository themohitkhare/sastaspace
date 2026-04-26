import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

type Project = {
  slug: string;
  title: string;
  blurb: string;
  status: string;
  tags: string[];
  url: string;
};

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

const projectsMock = vi.hoisted(() => ({ rows: [] as Project[] }));
vi.mock("@/lib/projects", () => ({
  get PROJECTS() {
    return projectsMock.rows;
  },
}));

import { ProjectsList } from "@/components/ProjectsList";

describe("ProjectsList", () => {
  it("renders the brand-correct empty state when no projects exist", () => {
    projectsMock.rows = [];
    render(<ProjectsList />);
    expect(
      screen.getByText("The workshop's quiet today. Come back soon."),
    ).toBeInTheDocument();
  });

  it("renders cards from the static PROJECTS list", () => {
    projectsMock.rows = sampleRows;
    render(<ProjectsList />);
    expect(screen.getByText("Notes")).toBeInTheDocument();
    expect(screen.getByText("Echo")).toBeInTheDocument();
    expect(screen.getByText("notes.sastaspace.com")).toBeInTheDocument();
    // chip text
    expect(screen.getByText("live")).toBeInTheDocument();
    expect(screen.getByText("wip")).toBeInTheDocument();
  });

  it("links each card to its url", () => {
    projectsMock.rows = sampleRows;
    render(<ProjectsList />);
    const link = screen.getByText("Notes").closest("a");
    expect(link?.getAttribute("href")).toBe("https://notes.sastaspace.com");
  });
});
