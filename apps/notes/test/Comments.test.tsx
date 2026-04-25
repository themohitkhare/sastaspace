import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";

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

vi.mock("@/lib/auth", () => ({
  subscribe: (fn: (s: null) => void) => { fn(null); return () => {}; },
  getSession: () => null,
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

describe("Comments — pagination", () => {
  const makeComments = (n: number): Comment[] =>
    Array.from({ length: n }, (_, i) => ({
      id: i + 1,
      postSlug: "x",
      authorName: `User${i + 1}`,
      body: `Comment ${i + 1}`,
      createdAt: Date.parse("2026-04-25T10:00:00Z") + i * 60_000,
      status: "approved",
    }));

  it("shows all comments and no button when count ≤ 5", () => {
    render(<Comments slug="x" />);
    act(() => emit!(makeComments(5)));
    expect(screen.getByText("User1")).toBeInTheDocument();
    expect(screen.getByText("User5")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /older comment/i })).toBeNull();
  });

  it("shows last 5 and a button when count > 5", () => {
    render(<Comments slug="x" />);
    act(() => emit!(makeComments(8)));
    // last 5: User4–User8
    expect(screen.queryByText("User1")).toBeNull();
    expect(screen.queryByText("User3")).toBeNull();
    expect(screen.getByText("User4")).toBeInTheDocument();
    expect(screen.getByText("User8")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /3 older comments/i })).toBeInTheDocument();
  });

  it("clicking show-older reveals all comments", () => {
    render(<Comments slug="x" />);
    act(() => emit!(makeComments(8)));
    fireEvent.click(screen.getByRole("button", { name: /older comments/i }));
    expect(screen.getByText("User1")).toBeInTheDocument();
    expect(screen.getByText("User8")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /older comments/i })).toBeNull();
  });

  it("new real-time comment is always visible while collapsed", () => {
    render(<Comments slug="x" />);
    act(() => emit!(makeComments(5)));
    // add a 6th comment — it should appear (last 5 now includes it)
    act(() => emit!(makeComments(6)));
    expect(screen.getByText("User6")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /1 older comment/i })).toBeInTheDocument();
    expect(screen.queryByText("User1")).toBeNull();
  });
});
