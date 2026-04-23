import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectCard, type Project } from "./project-card";

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 1,
    slug: "demo",
    name: "Demo",
    url: "https://demo.sastaspace.com/",
    description: "A demo project.",
    live_at: null,
    ...overrides,
  };
}

describe("ProjectCard", () => {
  it("uses explicit status when provided", () => {
    render(<ProjectCard project={makeProject({ status: "paused", live_at: "2026-01-01" })} />);
    expect(screen.getByLabelText("status: paused")).toBeDefined();
  });

  it("derives 'live' when live_at is set and no status", () => {
    render(<ProjectCard project={makeProject({ live_at: "2026-01-01" })} />);
    expect(screen.getByLabelText("status: live")).toBeDefined();
  });

  it("derives 'wip' when live_at is null and no status", () => {
    render(<ProjectCard project={makeProject({ live_at: null })} />);
    expect(screen.getByLabelText("status: wip")).toBeDefined();
  });

  it("strips protocol and trailing slash from hostname display", () => {
    render(<ProjectCard project={makeProject({ url: "https://demo.sastaspace.com/" })} />);
    expect(screen.getByText("demo.sastaspace.com")).toBeDefined();
  });

  it("renders up to 3 tags", () => {
    render(
      <ProjectCard
        project={makeProject({ tags: ["a", "b", "c", "d"] })}
      />,
    );
    expect(screen.getByText("a")).toBeDefined();
    expect(screen.getByText("b")).toBeDefined();
    expect(screen.getByText("c")).toBeDefined();
    expect(screen.queryByText("d")).toBeNull();
  });
});
