import { RiskCell, type RiskBand } from "./risk-cell";
import { Drawer } from "./drawer";

export type ResultData = {
  fromCity: string;
  toCity: string;
  dateLabel: string;
  seasonTag: string | null;
  delayPct: string;
  delayBand: RiskBand;
  delaySub: string;
  cancelPct: string;
  cancelBand: RiskBand;
  cancelSub: string;
  baggagePct: string;
  baggageBand: RiskBand;
  baggageSub: string;
  shortRead: {
    lead: string;
    leadEm: string;
    leadTail: string;
    body: string;
  };
};

type Props = { data: ResultData };

export function ResultCard({ data }: Props) {
  return (
    <section className="result" aria-live="polite" aria-label="flight risk">
      <div className="result-head">
        <div className="route">
          <span>{data.fromCity}</span>
          <span className="arrow">→</span>
          <span>{data.toCity}</span>
        </div>
        <div className="meta">
          {data.dateLabel}
          {data.seasonTag ? <span className="chip">{data.seasonTag}</span> : null}
        </div>
      </div>

      <div className="risk-grid">
        <RiskCell
          label="Delay over 2 hours"
          value={data.delayPct}
          subtext={data.delaySub}
          band={data.delayBand}
        />
        <RiskCell
          label="Cancellation"
          value={data.cancelPct}
          subtext={data.cancelSub}
          band={data.cancelBand}
        />
        <RiskCell
          label="Baggage trouble"
          value={data.baggagePct}
          subtext={data.baggageSub}
          band={data.baggageBand}
        />
      </div>

      <div className="short-read">
        <div className="eb">the short read</div>
        <p>
          {data.shortRead.lead} <em>{data.shortRead.leadEm}</em>
          {data.shortRead.leadTail}
        </p>
        <p>{data.shortRead.body}</p>
      </div>

      <div className="drawers">
        <Drawer summary="how we predict these numbers">
          <p>
            We use the DGCA&apos;s own monthly reports — on-time performance per airline,
            cancellation rate per airline, and grievance counts by category. We pull the last 24
            months, weight toward the same calendar month (so July draws from prior Julys), and
            blend across the carriers that actually fly this route.
          </p>
          <p>
            We don&apos;t predict your specific flight number. Nobody can — weather-day events,
            day-of-week traffic, and ATC queueing dominate at that granularity and aren&apos;t in
            any public dataset.
          </p>
          <p>
            Seasonal adjustments: monsoon (Jun–Sep) adds ~6 percentage points to delay odds on
            metro routes; Delhi fog (Dec–Jan) adds ~9. Both are baked into the numbers above.
          </p>
        </Drawer>

        <Drawer summary="what the common add-ons would actually cover">
          <p>
            <strong>Zero Cancellation plans</strong> (IndiGo, MakeMyTrip, EaseMyTrip) cover{" "}
            <em>voluntary</em> cancellation only — when you change your mind. Airline-caused
            cancels are already refunded under DGCA. Worth it if you&apos;re honestly ≥9% likely to
            cancel.
          </p>
          <p>
            <strong>Delay insurance</strong> (Tata AIG, bundled plans) pays out on delays above a
            threshold. On a monsoon flight, the usual trigger is 3+ hours — and you&apos;d still
            have to claim. Expected payout typically under the premium.
          </p>
          <p>
            <strong>Baggage cover</strong> (Blue Ribbon Bags etc.) only adds value above the
            ₹20,000 DGCA cap, and usually requires a 96-hour wait. On a short domestic, rarely
            worth it.
          </p>
        </Drawer>

        <Drawer summary="what DGCA already gives you for free">
          <p>
            <strong>Airline-caused cancellation:</strong> 100% refund plus alternate flight or cash
            compensation. CAR Section 3, Series M, Part IV.
          </p>
          <p>
            <strong>Baggage lost, damaged, or delayed:</strong> up to ₹20,000 per passenger on
            domestic sectors. File a PIR at the airport before leaving.
          </p>
          <p>
            <strong>Long delays:</strong> meals, hotel for overnight, or ₹2,000–₹4,000 monetary
            compensation — except when the cause is weather or another force majeure event.
          </p>
          <p>
            <strong>Denied boarding:</strong> up to ₹20,000 plus full refund if no alternate within
            24 hours.{" "}
            <a
              href="https://www.dgca.gov.in/digigov-portal/?page=jsp/dgca/InventoryList/headerblock/knowYour/index_files/KYR_portal.html"
              target="_blank"
              rel="noreferrer"
            >
              full DGCA Know Your Rights ↗
            </a>
          </p>
        </Drawer>
      </div>
    </section>
  );
}
