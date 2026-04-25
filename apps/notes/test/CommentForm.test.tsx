import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import type { Session } from "@/lib/auth";

const submitMock = vi.fn();
vi.mock("@/lib/comments", () => ({
  submitComment: (...args: unknown[]) => submitMock(...args),
  subscribeComments: () => () => {},
}));

let mockSession: Session | null = null;
vi.mock("@/lib/auth", () => ({
  subscribe: (fn: (s: Session | null) => void) => {
    fn(mockSession);
    return () => {};
  },
  getSession: () => mockSession,
}));

import { CommentForm } from "@/components/CommentForm";

afterEach(() => {
  submitMock.mockReset();
  mockSession = null;
});

describe("CommentForm — anonymous visitor", () => {
  it("shows sign-in gate, not a textarea", () => {
    render(<CommentForm slug="x" />);
    expect(screen.getByText(/sign in to leave a comment/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in to comment/i })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /comment/i })).toBeNull();
  });
});

describe("CommentForm — signed-in user", () => {
  beforeEach(() => {
    mockSession = { token: "tok", email: "user@x.com", display_name: "Tester", saved_at: 0 };
  });

  it("shows the form with posting-as note", () => {
    render(<CommentForm slug="x" />);
    expect(screen.getByText(/posting as/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /comment/i })).toBeInTheDocument();
  });

  it("rejects bodies under 4 chars without calling reducer", () => {
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByRole("textbox", { name: /comment/i }), { target: { value: "ab" } });
    fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    expect(submitMock).not.toHaveBeenCalled();
    expect(screen.getByText(/too short/i)).toBeInTheDocument();
  });

  it("calls submitComment with slug and trimmed body", async () => {
    submitMock.mockResolvedValueOnce(undefined);
    render(<CommentForm slug="my-post" />);
    fireEvent.change(screen.getByRole("textbox", { name: /comment/i }), {
      target: { value: "  hello world  " },
    });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(submitMock).toHaveBeenCalledWith("my-post", "hello world");
  });

  it("shows queued state after successful submit", async () => {
    submitMock.mockResolvedValueOnce(undefined);
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByRole("textbox", { name: /comment/i }), {
      target: { value: "hello world" },
    });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(screen.getByText(/moderator's looking it over/i)).toBeInTheDocument();
  });

  it("surfaces reducer errors", async () => {
    submitMock.mockRejectedValueOnce(new Error("rate limit: max 5 per 5min"));
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByRole("textbox", { name: /comment/i }), {
      target: { value: "hello world" },
    });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(screen.getByText(/rate limit/i)).toBeInTheDocument();
  });
});
