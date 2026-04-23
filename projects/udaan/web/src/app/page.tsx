"use client";

import { useState } from "react";
import "./udaan.css";
import { Topbar } from "@/components/udaan/topbar";
import { Hero } from "@/components/udaan/hero";
import { SearchBar, type SearchValue } from "@/components/udaan/search-bar";
import { ResultCard, type ResultData } from "@/components/udaan/result-card";
import { UdaanFooter } from "@/components/udaan/footer";

const DEFAULT_INPUT: SearchValue = {
  from: "DEL",
  to: "BOM",
  date: "2026-07-15",
};

// Static default that mirrors the mockup. Task 5 swaps this for computeRisk(data, input).
const DEFAULT_RESULT: ResultData = {
  fromCity: "Delhi",
  toCity: "Mumbai",
  dateLabel: "Wed, 15 Jul 2026",
  seasonTag: "peak monsoon",
  delayPct: "22%",
  delayBand: "mid",
  delaySub: "mid-risk · monsoon adds ~6pp",
  cancelPct: "1.8%",
  cancelBand: "low",
  cancelSub: "low · IndiGo 1.4, SpiceJet 2.5",
  baggagePct: "0.4%",
  baggageBand: "low",
  baggageSub: "low · within normal range",
  shortRead: {
    lead: "Mid-risk monsoon flight.",
    leadEm: "Delay is the main story",
    leadTail:
      " — roughly one in five flights on this route in July runs more than two hours late. But monsoon delays are treated as force majeure, so the airline isn’t liable for compensation.",
    body: "Cancellation and baggage risk are both low. DGCA already refunds airline-caused cancellations in full, and baggage liability is ₹20,000 per passenger before you pay anyone a paisa.",
  },
};

export default function UdaanPage() {
  const [input, setInput] = useState<SearchValue>(DEFAULT_INPUT);
  // Task 5 replaces this with derived state from computeRisk().
  const result = DEFAULT_RESULT;

  return (
    <div className="udaan">
      <div className="wrap">
        <Topbar />
        <Hero />
        <SearchBar value={input} onChange={setInput} />
        <div className="search-sub">
          Based on DGCA data through January 2026. No login, no emails, no tracking.
        </div>
        <ResultCard data={result} />
        <UdaanFooter />
      </div>
    </div>
  );
}
