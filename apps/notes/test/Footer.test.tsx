import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "@/components/Footer";

describe("Footer", () => {
  it("renders the brand sig + sastaspace link", () => {
    render(<Footer />);
    expect(screen.getByText(/built sasta/i)).toBeInTheDocument();
    const link = screen.getByText("sastaspace.com").closest("a");
    expect(link?.getAttribute("href")).toBe("https://sastaspace.com");
  });
});
