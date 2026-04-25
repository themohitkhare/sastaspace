import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { BrandMark } from "@/components/BrandMark";

describe("BrandMark", () => {
  it("renders an SVG with the wordmark glyph", () => {
    const { container } = render(<BrandMark />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("viewBox")).toBe("0 0 80 80");
    expect(container.querySelector("text")?.textContent).toBe("S");
  });

  it("uses brand colours (Ink fill on body, Sasta stroke on tag)", () => {
    const { container } = render(<BrandMark />);
    expect(container.querySelector('rect[fill="#1a1917"]')).not.toBeNull();
    expect(container.querySelector('path[stroke="#c05621"]')).not.toBeNull();
  });

  it("forwards className to the root svg", () => {
    const { container } = render(<BrandMark className="x" />);
    expect(container.querySelector("svg")?.getAttribute("class")).toBe("x");
  });
});
