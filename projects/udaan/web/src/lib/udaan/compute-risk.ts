import type {
  AirlineCode,
  AirlineMonthly,
  RiskInput,
  RiskResult,
  RouteRow,
  Routes,
  UdaanData,
} from "./types";
import type { RiskBand } from "@/components/udaan/risk-cell";

const METRO_CARRIERS: AirlineCode[] = [
  "IndiGo",
  "AirIndia",
  "SpiceJet",
  "Akasa",
  "Vistara",
];

const MONSOON_MONTHS = new Set([6, 7, 8, 9]);
const FOG_MONTHS = new Set([12, 1]);

function monthOf(iso: string): number {
  // "YYYY-MM-DD" → 1..12
  const m = /^\d{4}-(\d{2})-\d{2}$/.exec(iso);
  if (!m) return NaN;
  return Number(m[1]);
}

function sameDay(a: string, b: string): boolean {
  return a === b;
}

function classifyBand(pct: number, thresholds: [number, number]): RiskBand {
  const [low, high] = thresholds;
  if (pct < low) return "low";
  if (pct < high) return "mid";
  return "high";
}

function averageOtpForMonth(
  airlineMonthly: AirlineMonthly,
  airline: AirlineCode,
  month: number,
): number | null {
  const series = airlineMonthly[airline];
  if (!series) return null;
  // Same calendar month only (weighted toward prior Julys for a July query).
  const vals: number[] = [];
  for (const [ym, otp] of Object.entries(series)) {
    if (Number(ym.slice(5, 7)) === month) vals.push(otp);
  }
  if (vals.length === 0) {
    // Fall back to any-month average so unknown seasonality still answers.
    const allVals = Object.values(series);
    if (allVals.length === 0) return null;
    return allVals.reduce((a, b) => a + b, 0) / allVals.length;
  }
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function findRoute(routes: Routes, from: string, to: string): RouteRow | null {
  return (
    routes.routes.find((r) => r.from === from && r.to === to) ??
    // Treat route as symmetric if only the reverse is in the table.
    routes.routes.find((r) => r.from === to && r.to === from) ??
    null
  );
}

/**
 * Pure risk calculator. Deterministic given (input, data).
 *
 * Delay model: DGCA OTP measures flights on-time at 15 min. We approximate
 * the tail beyond 2 hours as ~25% of the overall delay mass, then add a
 * seasonal lift (monsoon ~6pp on metros, Delhi fog ~9pp).
 *
 * Cancellation model: blend the carriers that fly the route using the
 * hand-curated 12-month-per-airline baseline, weighted equally, with a
 * small season-pair lift.
 *
 * Baggage model: baseline 0.3% for metros, +0.1pp monsoon, +0.05pp fog.
 */
export function computeRisk(input: RiskInput, data: UdaanData): RiskResult {
  const { from, to, date } = input;
  const month = monthOf(date);
  if (!Number.isFinite(month)) throw new Error(`invalid date: ${date}`);
  if (sameDay(from, to)) throw new Error(`from and to must differ (${from})`);

  const route = findRoute(data.routes, from, to);
  const isMonsoon = MONSOON_MONTHS.has(month);
  const isFog = FOG_MONTHS.has(month);
  const delhiPair = from === "DEL" || to === "DEL";

  // ----- delay -----
  const carriers = (route?.carriers ?? METRO_CARRIERS) as AirlineCode[];
  const otps: number[] = [];
  for (const c of carriers) {
    const v = averageOtpForMonth(data.airlineMonthly, c, month);
    if (v != null) otps.push(v);
  }
  const avgOtp =
    otps.length > 0 ? otps.reduce((a, b) => a + b, 0) / otps.length : 85;
  const delayMass = Math.max(0, 100 - avgOtp); // % of flights delayed >=15m
  let delayPct = delayMass * 0.25; // tail at 2h+

  let delaySub = "within normal range";
  if (isMonsoon) {
    const monsoonLift = 6 * (route?.monsoonSeverity ?? 0.7);
    delayPct += monsoonLift;
    delaySub = `monsoon adds ~${Math.round(monsoonLift)}pp`;
  }
  if (isFog && delhiPair) {
    const fogLift = 9 * (route?.fogSeverity ?? 1.0);
    delayPct += fogLift;
    delaySub = `Delhi fog adds ~${Math.round(fogLift)}pp`;
  }
  delayPct = Math.min(60, Math.round(delayPct));
  const delayBand = classifyBand(delayPct, [15, 28]);

  // ----- cancellation -----
  const cancelSamples: { carrier: AirlineCode; pct: number }[] = [];
  for (const c of carriers) {
    const row = data.cancellation.baseline[c];
    if (row && row.length === 12) {
      cancelSamples.push({ carrier: c, pct: row[month - 1] });
    }
  }
  const cancelAvg =
    cancelSamples.length > 0
      ? cancelSamples.reduce((s, x) => s + x.pct, 0) / cancelSamples.length
      : 2.0;
  const cancelPct = Math.round(cancelAvg * 10) / 10;
  const cancelBand = classifyBand(cancelPct, [2.0, 3.2]);
  // Pick the two most-flown carriers to cite.
  const [c1, c2] = cancelSamples.slice(0, 2);
  const cancelSub = c1
    ? `${cancelBand === "low" ? "low" : cancelBand === "mid" ? "mid" : "elevated"} · ${c1.carrier} ${c1.pct}${
        c2 ? `, ${c2.carrier} ${c2.pct}` : ""
      }`
    : "baseline";

  // ----- baggage -----
  let baggagePct = 0.3;
  if (isMonsoon) baggagePct += 0.1;
  if (isFog) baggagePct += 0.05;
  baggagePct = Math.round(baggagePct * 10) / 10;
  const baggageBand = classifyBand(baggagePct, [0.5, 0.9]);
  const baggageSub =
    baggageBand === "low"
      ? "low · within normal range"
      : baggageBand === "mid"
        ? "mid · season lift"
        : "elevated · check weather advisories";

  // ----- season tag + copy -----
  let seasonTag: string | null = null;
  if (isMonsoon) seasonTag = "peak monsoon";
  else if (isFog && delhiPair) seasonTag = "Delhi fog window";
  else if (isFog) seasonTag = "winter";

  const shortRead = buildShortRead({
    delayPct,
    delayBand,
    cancelPct,
    cancelBand,
    isMonsoon,
    isFogDelhi: isFog && delhiPair,
  });

  return {
    delayPct,
    delayBand,
    delaySub: `${delayBand === "low" ? "low" : delayBand === "mid" ? "mid-risk" : "high-risk"} · ${delaySub}`,
    cancelPct,
    cancelBand,
    cancelSub,
    baggagePct,
    baggageBand,
    baggageSub,
    seasonTag,
    shortRead,
  };
}

function buildShortRead(args: {
  delayPct: number;
  delayBand: RiskBand;
  cancelPct: number;
  cancelBand: RiskBand;
  isMonsoon: boolean;
  isFogDelhi: boolean;
}): RiskResult["shortRead"] {
  const { delayBand, isMonsoon, isFogDelhi } = args;

  if (isFogDelhi) {
    return {
      lead: "Fog-season Delhi flight.",
      leadEm: "Delay risk is the big story",
      leadTail:
        " — Delhi-area December and January mornings routinely pile up 2+ hour delays when visibility drops. Airlines treat fog as force majeure, so no compensation for a delay alone.",
      body: "Cancellation stays in the normal band because DGCA already refunds airline-caused cancels in full, and baggage liability is ₹20,000 per passenger before you pay anyone a paisa.",
    };
  }
  if (isMonsoon && delayBand !== "low") {
    return {
      lead: "Mid-risk monsoon flight.",
      leadEm: "Delay is the main story",
      leadTail:
        " — roughly one in five flights on this route in peak monsoon runs more than two hours late. But monsoon delays are treated as force majeure, so the airline isn’t liable for compensation.",
      body: "Cancellation and baggage risk are both low. DGCA already refunds airline-caused cancellations in full, and baggage liability is ₹20,000 per passenger before you pay anyone a paisa.",
    };
  }
  if (delayBand === "high") {
    return {
      lead: "Elevated delay risk.",
      leadEm: "Plan a buffer on either side",
      leadTail: " — the headline number here is large enough to matter for connections or meetings.",
      body: "Cancellation and baggage baselines stay within the normal band. DGCA already covers airline-caused cancels; baggage liability is ₹20,000 per passenger on domestic sectors.",
    };
  }
  return {
    lead: "Low-risk route.",
    leadEm: "Numbers here are in the normal band",
    leadTail:
      " — delay, cancellation, and baggage risk are all within the range DGCA data shows for this month historically.",
    body: "The DGCA protections below apply regardless: 100% refund for airline-caused cancels, ₹20,000 baggage liability per passenger, and meals/hotel for long delays that aren’t weather-caused.",
  };
}
