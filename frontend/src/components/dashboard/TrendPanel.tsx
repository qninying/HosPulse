import type { HospitalDetail } from "@/lib/hospitalDetail";
import { formatMetric } from "@/lib/hospitalDetail";
import { Sparkline } from "./Sparkline";

type TrendPanelProps = {
  hospital: HospitalDetail;
};

type Series = { label: string; unit: string; pick: (y: HospitalDetail["years"][number]) => number | null };

const SERIES: Series[] = [
  { label: "Operating margin", unit: "%", pick: (y) => y.operating_margin_pct },
  { label: "Days cash on hand", unit: " days", pick: (y) => y.days_cash_on_hand },
  { label: "Days in A/R", unit: " days", pick: (y) => y.days_in_ar },
];

// Numbers first, chart as secondary reinforcement -- never chart-only. This
// product's whole trust model is exact, sourced figures, so the sparkline
// is a visual aid, not the source of truth.
export function TrendPanel({ hospital }: TrendPanelProps) {
  if (hospital.years.length === 0) {
    return <p className="dc-muted">No cost report data is available yet for this hospital.</p>;
  }

  return (
    <div className="dc-trend-grid">
      {SERIES.map((series) => (
        <div key={series.label} className="dc-trend-series">
          <div className="dc-trend-series-head">
            <span>{series.label}</span>
            <Sparkline points={hospital.years.map(series.pick)} />
          </div>
          <div className="dc-trend-values">
            {hospital.years.map((y) => (
              <span key={y.fiscal_year}>
                FY{y.fiscal_year}: {formatMetric(series.pick(y), series.unit)}
              </span>
            ))}
          </div>
        </div>
      ))}
      {hospital.years.length < 3 && (
        <p className="dc-muted dc-small">
          Only {hospital.years.length} fiscal year{hospital.years.length === 1 ? "" : "s"} on file for
          this hospital -- a real reporting gap, not an error.
        </p>
      )}
    </div>
  );
}
