# udaan data pipeline

Turns the DGCA Vonter CSVs (`../data-audit/vendor/aggregated/`) into three
JSON artifacts the web app serves from `/public/data/`.

## Run

```bash
node projects/udaan/data/etl.mjs
```

No dependencies; Node >= 18.

## Outputs

| file | source | notes |
|---|---|---|
| `out/airline-monthly.json` | `daily.csv` | OTP% per airline per `YYYY-MM`, averaged across days present in that month. |
| `out/cancellation.json` | hand-curated | DGCA CSVs don't carry cancellation as a column (AUDIT Q1 = red), so this is a 12-month baseline per airline seeded from published monthly summaries. |
| `out/routes.json` | derived | Metro-metro pair table with monsoon/fog severity multipliers and typical carriers. |

The script also writes the same files into `../web/public/data/` so the
built frontend can fetch them without a build-time bundler step.

## Data gaps the audit surfaced (carried into `computeRisk`)

- **No direct cancellation column** — fall back to the hand-curated baseline.
- **No direct delay-over-2h column** — approximate from `100 - OTP%` scaled.
- **No grievance-rate-per-passenger** — baggage risk uses a fixed low baseline
  with seasonal adjustments rather than a true rate.
