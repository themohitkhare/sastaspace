import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusChip } from "./status-chip";

describe("StatusChip", () => {
  const cases = [
    { value: "live", label: "live" },
    { value: "wip", label: "wip" },
    { value: "paused", label: "paused" },
    { value: "archived", label: "archived" },
    { value: "open-source", label: "open source" },
  ] as const;

  for (const { value, label } of cases) {
    it(`renders ${value} with label "${label}" and aria-label`, () => {
      render(<StatusChip value={value} />);
      const chip = screen.getByLabelText(`status: ${label}`);
      expect(chip).toBeDefined();
      expect(chip.textContent).toBe(label);
    });
  }
});
