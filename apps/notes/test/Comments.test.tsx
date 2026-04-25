import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";

type Comment = {
  id: number;
  postSlug: string;
  authorName: string;
  body: string;
  createdAt: number;
  status: string;
};

let emit: ((rows: readonly Comment[]) => void) | null = null;
vi.mock("@/lib/comments", () => ({
  subscribeComments: (_: string, fn: (rows: readonly Comment[]) => void) => {
    emit = fn;
    fn([]);
    return () => {
      emit = null;
    };
  },
  submitComment: vi.fn(),
}));

import { Comments } from "@/components/Comments";

afterEach(() => {
  emit = null;
});

const sample: Comment[] = [
  {
    id: 1,
    postSlug: "x",
    authorName: "Alice",
    body: "Nice post.",
    createdAt: Date.parse("2026-04-25T10:00:00Z"),
    status: "approved",
  },
  {
    id: 2,
    postSlug: "x",
    authorName: "Bob",
    body: "Agree.",
    createdAt: Date.parse("2026-04-25T11:00:00Z"),
    status: "approved",
  },
];

describe("Comments", () => {
  it("shows empty state when no comments", () => {
    render(<Comments slug="x" />);
    expect(screen.getByText(/be the first to break the silence/i)).toBeInTheDocument();
  });

  it("renders comments when subscription delivers them", () => {
    render(<Comments slug="x" />);
    act(() => emit!(sample));
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Nice post.")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("falls back to empty state when comments clear", () => {
    render(<Comments slug="x" />);
    act(() => emit!(sample));
    act(() => emit!([]));
    expect(screen.getByText(/be the first/i)).toBeInTheDocument();
  });
});
