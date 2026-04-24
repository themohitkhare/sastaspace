import { describe, test, expect } from "vitest";
import { publicOrigin } from "./public-origin";

function reqWith(url: string, headers: Record<string, string> = {}): Request {
  return new Request(url, { headers });
}

describe("publicOrigin", () => {
  test("uses x-forwarded-host, always https for public hosts", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "sastaspace.com",
      "x-forwarded-proto": "https",
    });
    expect(publicOrigin(r)).toBe("https://sastaspace.com");
  });

  test("forces https even when x-forwarded-proto is http (Cloudflare → tunnel → ingress is http)", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "sastaspace.com",
      "x-forwarded-proto": "http",
    });
    expect(publicOrigin(r)).toBe("https://sastaspace.com");
  });

  test("falls back to host header when x-forwarded-host is missing", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      host: "almirah.sastaspace.com",
    });
    expect(publicOrigin(r)).toBe("https://almirah.sastaspace.com");
  });

  test("keeps http for localhost dev", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      host: "localhost:3000",
    });
    expect(publicOrigin(r)).toBe("http://localhost:3000");
  });

  test("last-resort falls back to request URL origin", () => {
    const r = reqWith("http://localhost:3000/foo");
    expect(publicOrigin(r)).toBe("http://localhost:3000");
  });

  test("never returns 0.0.0.0 when any host header exists", () => {
    const r = reqWith("http://0.0.0.0:3000/foo", {
      "x-forwarded-host": "sastaspace.com",
    });
    expect(publicOrigin(r)).not.toContain("0.0.0.0");
  });
});
