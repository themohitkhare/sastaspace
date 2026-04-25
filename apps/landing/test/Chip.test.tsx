import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Chip } from "@/components/Chip";

describe("Chip", () => {
  it("renders the variant label as text", () => {
    render(<Chip variant="live" />);
    expect(screen.getByText("live")).toBeInTheDocument();
  });

  it.each(["live", "wip", "paused", "open source", "archived"] as const)(
    "renders %s without throwing",
    (variant) => {
      render(<Chip variant={variant} />);
      expect(screen.getByText(variant)).toBeInTheDocument();
    },
  );
});
