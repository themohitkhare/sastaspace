import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Footer } from "@/components/Footer";

describe("Footer", () => {
  it("renders the brand sig", () => {
    render(<Footer />);
    expect(screen.getByText(/built/i)).toBeInTheDocument();
    expect(screen.getByText(/Mohit Khare/i)).toBeInTheDocument();
  });

  it("links to the real GitHub profile (themohitkhare)", () => {
    render(<Footer />);
    expect(screen.getByText("github").closest("a")?.getAttribute("href")).toBe(
      "https://github.com/themohitkhare",
    );
  });

  it("links to the real LinkedIn profile (themohitkhare)", () => {
    render(<Footer />);
    expect(
      screen.getByText("linkedin").closest("a")?.getAttribute("href"),
    ).toBe("https://www.linkedin.com/in/themohitkhare");
  });

  it("notes link points to subdomain", () => {
    render(<Footer />);
    expect(screen.getByText("notes").closest("a")?.getAttribute("href")).toBe(
      "https://notes.sastaspace.com",
    );
  });

  it("email link uses mailto:", () => {
    render(<Footer />);
    expect(screen.getByText("email").closest("a")?.getAttribute("href")).toBe(
      "mailto:hi@sastaspace.com",
    );
  });
});
