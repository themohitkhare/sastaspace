"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "./udaan.css";
import { Topbar } from "@/components/udaan/topbar";
import { Hero } from "@/components/udaan/hero";
import { SearchBar, type SearchValue } from "@/components/udaan/search-bar";
import { ResultCard, type ResultData } from "@/components/udaan/result-card";
import { UdaanFooter } from "@/components/udaan/footer";
import { computeRisk } from "@/lib/udaan/compute-risk";
import { cityOf } from "@/lib/udaan/airports";
import type {
  AirlineMonthly,
  CancellationBaseline,
  RiskInput,
  Routes,
  UdaanData,
} from "@/lib/udaan/types";

const DEFAULT_INPUT: SearchValue = {
  from: "DEL",
  to: "BOM",
  date: "2026-07-15",
};

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function parseHash(): SearchValue | null {
  if (typeof window === "undefined") return null;
  const h = window.location.hash.replace(/^#/, "");
  const m = /^([A-Z]{3})-([A-Z]{3})-(\d{4}-\d{2}-\d{2})$/.exec(h);
  if (!m) return null;
  return { from: m[1], to: m[2], date: m[3] };
}

function encodeHash(v: SearchValue): string {
  return `#${v.from}-${v.to}-${v.date}`;
}

function formatDateLabel(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  const [, y, mm, dd] = m;
  const dt = new Date(Date.UTC(Number(y), Number(mm) - 1, Number(dd)));
  return `${DAY_NAMES[dt.getUTCDay()]}, ${Number(dd)} ${MONTH_NAMES[Number(mm) - 1]} ${y}`;
}

function buildErrorResult(input: SearchValue, message: string): ResultData {
  return {
    fromCity: cityOf(input.from),
    toCity: cityOf(input.to),
    dateLabel: formatDateLabel(input.date),
    seasonTag: null,
    delayPct: "—",
    delayBand: "low",
    delaySub: message,
    cancelPct: "—",
    cancelBand: "low",
    cancelSub: message,
    baggagePct: "—",
    baggageBand: "low",
    baggageSub: message,
    shortRead: {
      lead: "Pick two different cities.",
      leadEm: "",
      leadTail: "",
      body: "udaan reads one-way risk between two different airports.",
    },
  };
}

function buildLoadingResult(input: SearchValue): ResultData {
  return {
    fromCity: cityOf(input.from),
    toCity: cityOf(input.to),
    dateLabel: formatDateLabel(input.date),
    seasonTag: null,
    delayPct: "…",
    delayBand: "low",
    delaySub: "loading DGCA data",
    cancelPct: "…",
    cancelBand: "low",
    cancelSub: "loading DGCA data",
    baggagePct: "…",
    baggageBand: "low",
    baggageSub: "loading DGCA data",
    shortRead: {
      lead: "Loading the numbers.",
      leadEm: "",
      leadTail: "",
      body: "Pulling the DGCA monthly series from /data — this is a one-time fetch.",
    },
  };
}

function adaptRisk(input: SearchValue, data: UdaanData): ResultData {
  const riskInput: RiskInput = { from: input.from, to: input.to, date: input.date };
  const risk = computeRisk(riskInput, data);
  return {
    fromCity: cityOf(input.from),
    toCity: cityOf(input.to),
    dateLabel: formatDateLabel(input.date),
    seasonTag: risk.seasonTag,
    delayPct: `${risk.delayPct}%`,
    delayBand: risk.delayBand,
    delaySub: risk.delaySub,
    cancelPct: `${risk.cancelPct}%`,
    cancelBand: risk.cancelBand,
    cancelSub: risk.cancelSub,
    baggagePct: `${risk.baggagePct}%`,
    baggageBand: risk.baggageBand,
    baggageSub: risk.baggageSub,
    shortRead: risk.shortRead,
  };
}

export default function UdaanPage() {
  const [input, setInput] = useState<SearchValue>(DEFAULT_INPUT);
  const [data, setData] = useState<UdaanData | null>(null);
  const [hashHydrated, setHashHydrated] = useState(false);
  const lastHashRef = useRef<string>("");

  // Hydrate from URL hash once on mount. This is the canonical pattern for
  // syncing client-only URL state into React state after SSR hydration;
  // it can't be expressed with a useState initializer without risking a
  // hydration mismatch when the hash is non-empty.
  useEffect(() => {
    const fromHash = parseHash();
    if (fromHash) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setInput(fromHash);
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHashHydrated(true);

    const onHashChange = () => {
      const next = parseHash();
      if (next && encodeHash(next) !== lastHashRef.current) {
        setInput(next);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Fetch the three data bundles in parallel, once.
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch("/data/airline-monthly.json").then((r) => r.json() as Promise<AirlineMonthly>),
      fetch("/data/cancellation.json").then((r) => r.json() as Promise<CancellationBaseline>),
      fetch("/data/routes.json").then((r) => r.json() as Promise<Routes>),
    ])
      .then(([airlineMonthly, cancellation, routes]) => {
        if (cancelled) return;
        setData({ airlineMonthly, cancellation, routes });
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("[udaan] data fetch failed", err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Mirror state into the URL hash.
  useEffect(() => {
    if (!hashHydrated) return;
    const next = encodeHash(input);
    if (next !== window.location.hash) {
      window.history.replaceState(null, "", next);
    }
    lastHashRef.current = next;
  }, [input, hashHydrated]);

  // Keep users out of the "from == to" state without scolding them.
  const safeOnChange = (v: SearchValue) => {
    if (v.from === v.to) {
      // If they just changed `to`, bump `from` to something else, and vice versa.
      if (v.to !== input.to) {
        const fallback = input.from !== v.to ? input.from : input.to;
        setInput({ ...v, from: fallback });
        return;
      }
      if (v.from !== input.from) {
        const fallback = input.to !== v.from ? input.to : input.from;
        setInput({ ...v, to: fallback });
        return;
      }
    }
    setInput(v);
  };

  const result = useMemo<ResultData>(() => {
    if (!data) return buildLoadingResult(input);
    if (input.from === input.to) return buildErrorResult(input, "pick two different airports");
    try {
      return adaptRisk(input, data);
    } catch (err) {
      console.error("[udaan] computeRisk failed", err);
      return buildErrorResult(input, "couldn't compute risk");
    }
  }, [input, data]);

  return (
    <div className="udaan">
      <div className="wrap">
        <Topbar />
        <Hero />
        <SearchBar value={input} onChange={safeOnChange} />
        <div className="search-sub">
          Based on DGCA data through January 2026. No login, no emails, no tracking.
        </div>
        <ResultCard data={result} />
        <UdaanFooter />
      </div>
    </div>
  );
}
