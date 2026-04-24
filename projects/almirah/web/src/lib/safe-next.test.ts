import { describe, test, expect } from "vitest";
import { getSafeNext } from "./safe-next";

const currentOrigin = "https://sastaspace.com";

describe("getSafeNext", () => {
  test("returns '/' for null input", () => {
    expect(getSafeNext(null, currentOrigin)).toBe("/");
  });

  test("returns '/' for empty string", () => {
    expect(getSafeNext("", currentOrigin)).toBe("/");
  });

  test("returns same-origin absolute path as-is", () => {
    expect(getSafeNext("/dashboard", currentOrigin)).toBe("/dashboard");
  });

  test("returns same-origin path with query as-is", () => {
    expect(getSafeNext("/dashboard?foo=bar", currentOrigin)).toBe(
      "/dashboard?foo=bar",
    );
  });

  test("rejects scheme-relative URL (protocol-relative // open-redirect)", () => {
    expect(getSafeNext("//evil.com", currentOrigin)).toBe("/");
    expect(getSafeNext("///evil.com", currentOrigin)).toBe("/");
  });

  test("rejects backslash-tricky scheme-relative URL", () => {
    expect(getSafeNext("/\\evil.com", currentOrigin)).toBe("/");
  });

  test("returns full URL on allowed *.sastaspace.com subdomain", () => {
    expect(
      getSafeNext("https://almirah.sastaspace.com/", currentOrigin),
    ).toBe("https://almirah.sastaspace.com/");
  });

  test("returns full URL with path + query on allowed subdomain", () => {
    expect(
      getSafeNext(
        "https://almirah.sastaspace.com/onboarding?first=1",
        currentOrigin,
      ),
    ).toBe("https://almirah.sastaspace.com/onboarding?first=1");
  });

  test("allows the apex domain itself", () => {
    expect(getSafeNext("https://sastaspace.com/foo", currentOrigin)).toBe(
      "https://sastaspace.com/foo",
    );
  });

  test("rejects unrelated host masquerading as subdomain", () => {
    expect(
      getSafeNext("https://sastaspace.com.evil.com/", currentOrigin),
    ).toBe("/");
  });

  test("rejects http:// on a *.sastaspace.com subdomain (must be https)", () => {
    expect(
      getSafeNext("http://almirah.sastaspace.com/", currentOrigin),
    ).toBe("/");
  });

  test("rejects totally unrelated domain", () => {
    expect(getSafeNext("https://evil.com/", currentOrigin)).toBe("/");
  });

  test("rejects user-info injection to spoof host", () => {
    expect(
      getSafeNext(
        "https://sastaspace.com@evil.com/",
        currentOrigin,
      ),
    ).toBe("/");
  });

  test("rejects javascript: URL", () => {
    expect(getSafeNext("javascript:alert(1)", currentOrigin)).toBe("/");
  });

  test("rejects data: URL", () => {
    expect(getSafeNext("data:text/html,<script>1</script>", currentOrigin)).toBe(
      "/",
    );
  });

  test("rejects garbage input", () => {
    expect(getSafeNext("not a url", currentOrigin)).toBe("/");
  });
});
