import type { RiskBand } from "@/components/udaan/risk-cell";

export type AirlineCode =
  | "IndiGo"
  | "AirIndia"
  | "SpiceJet"
  | "Vistara"
  | "Akasa"
  | "AirAsia"
  | "GoAir"
  | "AllianceAir";

export type AirlineMonthly = Record<AirlineCode, Record<string, number>>;
// key format: YYYY-MM → average OTP percent (0..100)

export type CancellationBaseline = {
  notes: { source: string; unit: string; generatedAt: string };
  baseline: Record<AirlineCode, number[]>; // 12 entries Jan..Dec
};

export type RouteRow = {
  from: string;
  to: string;
  monsoonSeverity: number; // 0..1
  fogSeverity: number; // 0..1
  carriers: AirlineCode[];
};

export type Routes = {
  notes: { source: string; unit: string; generatedAt: string };
  routes: RouteRow[];
};

export type UdaanData = {
  airlineMonthly: AirlineMonthly;
  cancellation: CancellationBaseline;
  routes: Routes;
};

export type RiskInput = {
  from: string; // IATA
  to: string; // IATA
  date: string; // YYYY-MM-DD
};

export type RiskResult = {
  delayPct: number; // percent of flights delayed >= 2h (0..100)
  delayBand: RiskBand;
  delaySub: string;
  cancelPct: number;
  cancelBand: RiskBand;
  cancelSub: string;
  baggagePct: number;
  baggageBand: RiskBand;
  baggageSub: string;
  seasonTag: string | null;
  shortRead: {
    lead: string;
    leadEm: string;
    leadTail: string;
    body: string;
  };
};
