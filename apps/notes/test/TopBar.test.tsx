import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopBar } from "@/components/TopBar";

describe("TopBar", () => {
  it("links back to the lab home", () => {
    render(<TopBar />);
    const home = screen.getByText(/home/i).closest("a");
    expect(home?.getAttribute("href")).toBe("https://sastaspace.com");
  });

  it("identifies the current section as notes", () => {
    render(<TopBar />);
    expect(screen.getByText(/notes/i)).toBeInTheDocument();
  });
});
