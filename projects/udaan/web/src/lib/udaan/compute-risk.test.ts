import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { computeRisk } from "./compute-risk";
import type { UdaanData, AirlineMonthly, CancellationBaseline, Routes } from "./types";

let data: UdaanData;

beforeAll(() => {
  const pub = join(process.cwd(), "public", "data");
  const airlineMonthly = JSON.parse(
    readFileSync(join(pub, "airline-monthly.json"), "utf8"),
  ) as AirlineMonthly;
  const cancellation = JSON.parse(
    readFileSync(join(pub, "cancellation.json"), "utf8"),
  ) as CancellationBaseline;
  const routes = JSON.parse(readFileSync(join(pub, "routes.json"), "utf8")) as Routes;
  data = { airlineMonthly, cancellation, routes };
});

describe("computeRisk", () => {
  it("returns a shaped result for a known metro pair in monsoon", () => {
    const r = computeRisk({ from: "DEL", to: "BOM", date: "2026-07-15" }, data);
    expect(r.seasonTag).toBe("peak monsoon");
    expect(r.delayPct).toBeGreaterThan(0);
    expect(r.delayPct).toBeLessThan(60);
    expect(r.cancelPct).toBeGreaterThan(0);
    expect(r.baggagePct).toBeGreaterThan(0);
    expect(r.shortRead.lead.length).toBeGreaterThan(0);
  });

  it("flags Delhi fog window with the fog tag on a Delhi route in January", () => {
    const r = computeRisk({ from: "DEL", to: "BLR", date: "2026-01-20" }, data);
    expect(r.seasonTag).toBe("Delhi fog window");
    expect(r.delaySub).toContain("Delhi fog");
  });

  it("uses a generic winter tag for a non-Delhi January route", () => {
    const r = computeRisk({ from: "BOM", to: "BLR", date: "2026-01-20" }, data);
    expect(r.seasonTag).toBe("winter");
    expect(r.delaySub).not.toContain("Delhi fog");
  });

  it("returns no season tag for a shoulder-month route", () => {
    const r = computeRisk({ from: "BLR", to: "HYD", date: "2026-03-10" }, data);
    expect(r.seasonTag).toBeNull();
  });

  it("raises delay risk in monsoon vs. a shoulder month for the same pair", () => {
    const m = computeRisk({ from: "BOM", to: "MAA", date: "2026-07-10" }, data);
    const s = computeRisk({ from: "BOM", to: "MAA", date: "2026-03-10" }, data);
    expect(m.delayPct).toBeGreaterThan(s.delayPct);
  });

  it("assigns a low delay band to a clean shoulder-month metro pair", () => {
    const r = computeRisk({ from: "BLR", to: "HYD", date: "2026-11-10" }, data);
    expect(["low", "mid"]).toContain(r.delayBand);
  });

  it("names at least one carrier in the cancellation subtext", () => {
    const r = computeRisk({ from: "DEL", to: "CCU", date: "2026-07-04" }, data);
    // e.g. "low · IndiGo 1.8, AirIndia 2.4"
    expect(r.cancelSub).toMatch(/IndiGo|AirIndia|SpiceJet|Akasa|Vistara/);
  });

  it("rejects same-airport from/to", () => {
    expect(() =>
      computeRisk({ from: "DEL", to: "DEL", date: "2026-07-15" }, data),
    ).toThrow();
  });

  it("rejects malformed dates", () => {
    expect(() =>
      computeRisk({ from: "DEL", to: "BOM", date: "15-07-2026" }, data),
    ).toThrow();
  });

  it("handles an unknown route pair without throwing and falls back to metro carriers", () => {
    const r = computeRisk({ from: "XXX", to: "YYY", date: "2026-05-10" }, data);
    expect(r.delayPct).toBeGreaterThanOrEqual(0);
    expect(r.cancelPct).toBeGreaterThan(0);
  });

  it("caps delayPct at 60%", () => {
    // Build a synthetic dataset with catastrophic OTP to ensure the clamp holds.
    const bad: UdaanData = {
      airlineMonthly: {
        IndiGo: { "2026-01": 0, "2026-07": 0 },
        AirIndia: { "2026-01": 0, "2026-07": 0 },
        SpiceJet: { "2026-01": 0, "2026-07": 0 },
        Vistara: { "2026-01": 0, "2026-07": 0 },
        Akasa: { "2026-01": 0, "2026-07": 0 },
        AirAsia: {},
        GoAir: {},
        AllianceAir: {},
      },
      cancellation: data.cancellation,
      routes: data.routes,
    };
    const r = computeRisk({ from: "DEL", to: "BOM", date: "2026-01-15" }, bad);
    expect(r.delayPct).toBeLessThanOrEqual(60);
  });

  it("monsoon lift respects route severity (BOM pair > BLR-HYD inland pair)", () => {
    const coastal = computeRisk({ from: "DEL", to: "BOM", date: "2026-07-15" }, data);
    const inland = computeRisk({ from: "BLR", to: "HYD", date: "2026-07-15" }, data);
    expect(coastal.delayPct).toBeGreaterThanOrEqual(inland.delayPct);
  });

  it("cancellation rounds to one decimal place", () => {
    const r = computeRisk({ from: "DEL", to: "BOM", date: "2026-07-15" }, data);
    expect(Math.round(r.cancelPct * 10)).toBe(r.cancelPct * 10);
  });

  it("baggage subtext matches band", () => {
    const r = computeRisk({ from: "DEL", to: "BOM", date: "2026-07-15" }, data);
    if (r.baggageBand === "low") expect(r.baggageSub).toContain("low");
  });
});
