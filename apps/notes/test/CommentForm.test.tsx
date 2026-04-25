import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";

const submitMock = vi.fn();
vi.mock("@/lib/comments", () => ({
  submitComment: (...args: unknown[]) => submitMock(...args),
  subscribeComments: () => () => {},
}));

import { CommentForm } from "@/components/CommentForm";

afterEach(() => {
  submitMock.mockReset();
});

describe("CommentForm", () => {
  it("rejects empty bodies under 4 chars without calling reducer", () => {
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByLabelText(/comment/i), { target: { value: "ab" } });
    fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    expect(submitMock).not.toHaveBeenCalled();
    expect(screen.getByText(/too short/i)).toBeInTheDocument();
  });

  it("calls submitComment with trimmed name + body", async () => {
    submitMock.mockResolvedValueOnce(undefined);
    render(<CommentForm slug="my-post" />);
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "  Mohit  " } });
    fireEvent.change(screen.getByLabelText(/comment/i), { target: { value: "  hi there  " } });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(submitMock).toHaveBeenCalledWith("my-post", "Mohit", "hi there");
  });

  it("shows queued state after successful submit", async () => {
    submitMock.mockResolvedValueOnce(undefined);
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByLabelText(/comment/i), { target: { value: "hello world" } });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(screen.getByText(/moderator's looking it over/i)).toBeInTheDocument();
  });

  it("surfaces reducer errors", async () => {
    submitMock.mockRejectedValueOnce(new Error("rate limit: max 5 per 5min"));
    render(<CommentForm slug="x" />);
    fireEvent.change(screen.getByLabelText(/comment/i), { target: { value: "hello world" } });
    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: /post comment/i }).closest("form")!);
    });
    expect(screen.getByText(/rate limit/i)).toBeInTheDocument();
  });
});
