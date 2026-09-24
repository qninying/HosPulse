import Link from "next/link";
import "../../public.css";
import {
  DATA_LAG_NOTE,
  formatMetric,
  getHospitalTrends,
} from "@/lib/hospitalDetail";

type PageProps = {
  params: Promise<{ ccn: string }>;
};

// Same thresholds early_warning.py's engine evaluates the latest fiscal
// year against (OPERATING_MARGIN_THRESHOLD_PCT / DAYS_CASH_ON_HAND_THRESHOLD_DAYS).
// Re-checking them here only changes how the number is displayed (flagged
// red on the latest row), never what number is shown -- the underlying
// value always comes straight from the query, formatted the same way
// regardless of this check.
const OPERATING_MARGIN_THRESHOLD_PCT = 0;
const DAYS_CASH_ON_HAND_THRESHOLD_DAYS = 30;

export default async function HospitalPage({ params }: PageProps) {
  const { ccn } = await params;
  const outcome = await getHospitalTrends(ccn);

  if (!outcome.ok && outcome.kind === "not_found") {
    return (
      <main className="hp-shell">
        <div className="hp-content-narrow">
          <Link href="/" className="hp-back-link">
            &larr; Back to search
          </Link>
          <h1>Hospital not found</h1>
          <p className="hp-lede" style={{ margin: "8px 0 0", textAlign: "left" }}>
            No hospital matches &quot;{ccn}&quot;.
          </p>
        </div>
      </main>
    );
  }

  if (!outcome.ok) {
    return (
      <main className="hp-shell">
        <div className="hp-content-narrow">
          <Link href="/" className="hp-back-link">
            &larr; Back to search
          </Link>
          <h1>Data retrieval error</h1>
          <p className="hp-alert hp-alert-danger" role="alert" style={{ marginTop: 16 }}>
            We couldn&apos;t retrieve this hospital&apos;s data right now. ({outcome.error})
          </p>
        </div>
      </main>
    );
  }

  const { hospital } = outcome;
  const latestYear = hospital.years[hospital.years.length - 1];

  return (
    <main className="hp-shell">
      <div className="hp-content-narrow">
        <Link href="/" className="hp-back-link">
          &larr; Back to search
        </Link>

        <div className="hp-detail-head">
          <h1>{hospital.name ?? "(name not yet resolved)"}</h1>
          <span className="hp-state-badge">{hospital.state}</span>
        </div>
        <p className="hp-lag-note">{DATA_LAG_NOTE}</p>

        {hospital.years.length === 0 ? (
          <p className="hp-empty">No cost report data is available yet for this hospital.</p>
        ) : (
          <div className="hp-metrics-card">
            <table className="hp-metrics-table">
              <thead>
                <tr>
                  <th>Fiscal year</th>
                  <th>Operating margin</th>
                  <th>Days cash on hand</th>
                  <th>Days in A/R</th>
                </tr>
              </thead>
              <tbody>
                {hospital.years.map((y) => {
                  const isLatest = y.fiscal_year === latestYear.fiscal_year;
                  const marginFlagged =
                    isLatest &&
                    y.operating_margin_pct !== null &&
                    y.operating_margin_pct < OPERATING_MARGIN_THRESHOLD_PCT;
                  const cashFlagged =
                    isLatest &&
                    y.days_cash_on_hand !== null &&
                    y.days_cash_on_hand < DAYS_CASH_ON_HAND_THRESHOLD_DAYS;
                  return (
                    <tr key={y.fiscal_year} className={isLatest ? "hp-row-latest" : undefined}>
                      <td>FY{y.fiscal_year}</td>
                      <td className={marginFlagged ? "hp-metric-flagged" : undefined}>
                        {formatMetric(y.operating_margin_pct, "%")}
                      </td>
                      <td className={cashFlagged ? "hp-metric-flagged" : undefined}>
                        {formatMetric(y.days_cash_on_hand, " days")}
                      </td>
                      <td>{formatMetric(y.days_in_ar, " days")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {hospital.years.length > 0 && (
          <p className="hp-threshold-note">
            Highlighted values on the most recent year are below the same thresholds HosPulse&apos;s
            early-warning engine uses: an operating margin under 0% or fewer than 30 days cash on
            hand.
          </p>
        )}

        {hospital.years.length > 0 && hospital.years.length < 3 && (
          <p className="hp-gap-note">
            Only {hospital.years.length} year
            {hospital.years.length === 1 ? "" : "s"} of data{" "}
            {hospital.years.length === 1 ? "is" : "are"} available for this
            hospital in the public CMS filings -- a real reporting gap, not an
            error.
          </p>
        )}
      </div>
    </main>
  );
}
