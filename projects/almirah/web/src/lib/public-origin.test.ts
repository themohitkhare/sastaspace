import { describe, test, expect } from "vitest";
import { publicOrigin } from "./public-origin";

function reqWith(url: string, headers: Record<string, string> = {}): Request {
  return new Request(url, { headers });
}

describe("publicOrigin", () => {
  test("uses x-forwarded-host + x-forwarded-proto when present", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "sastaspace.com",
      "x-forwarded-proto": "https",
    });
    expect(publicOrigin(r)).toBe("https://sastaspace.com");
  });

  test("falls back to host header when x-forwarded-host is missing", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      host: "sastaspace.com",
      "x-forwarded-proto": "https",
    });
    expect(publicOrigin(r)).toBe("https://sastaspace.com");
  });

  test("defaults scheme to https when x-forwarded-proto is absent", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "almirah.sastaspace.com",
    });
    expect(publicOrigin(r)).toBe("https://almirah.sastaspace.com");
  });

  test("last-resort falls back to request URL origin", () => {
    const r = reqWith("http://localhost:3000/foo");
    expect(publicOrigin(r)).toBe("http://localhost:3000");
  });

  test("never returns 0.0.0.0 when forwarded headers exist", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "sastaspace.com",
    });
    expect(publicOrigin(r)).not.toContain("0.0.0.0");
  });
});
