/**
 * Tests for the client-side auth state management.
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSession, getSession, requestMagicLink, saveSession, subscribe } from "@/lib/auth";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("auth session storage", () => {
  it("returns null when no session is stored", () => {
    expect(getSession()).toBeNull();
  });

  it("saves and round-trips a session", () => {
    saveSession("token123", "user@example.com");
    const s = getSession();
    expect(s).not.toBeNull();
    expect(s?.token).toBe("token123");
    expect(s?.email).toBe("user@example.com");
    expect(s?.display_name).toBe("user");
  });

  it("clearSession removes it", () => {
    saveSession("t", "a@b.com");
    clearSession();
    expect(getSession()).toBeNull();
  });

  it("notifies subscribers on save and clear", () => {
    const fn = vi.fn();
    const unsub = subscribe(fn);
    fn.mockClear();
    saveSession("t", "x@y.com");
    expect(fn).toHaveBeenLastCalledWith(expect.objectContaining({ email: "x@y.com" }));
    clearSession();
    expect(fn).toHaveBeenLastCalledWith(null);
    unsub();
  });

  it("ignores malformed JSON in storage", () => {
    window.localStorage.setItem("sastaspace.auth.v1", "{not-json");
    expect(getSession()).toBeNull();
  });
});

describe("requestMagicLink", () => {
  it("posts to the auth service", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", mockFetch);
    await requestMagicLink("u@example.com");
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/auth\/request$/);
    expect(opts.method).toBe("POST");
    expect(opts.body).toContain("u@example.com");
  });

  it("throws with detail on HTTP error", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: () => Promise.resolve({ detail: "email send failed" }),
    });
    vi.stubGlobal("fetch", mockFetch);
    await expect(requestMagicLink("u@e.com")).rejects.toThrow("email send failed");
  });
});
