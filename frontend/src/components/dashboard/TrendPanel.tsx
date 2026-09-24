import type { HospitalDetail } from "@/lib/hospitalDetail";
import { formatMetric } from "@/lib/hospitalDetail";
import { TrendChart } from "./TrendChart";

type TrendPanelProps = {
  hospital: HospitalDetail;
};

type Series = {
  label: string;
  unit: string;
  pick: (y: HospitalDetail["years"][number]) => number | null;
  // Same constants early_warning.py evaluates the latest fiscal year
  // against; undefined for a metric with no single-value threshold.
  criticalBelow?: number;
};

const SERIES: Series[] = [
  { label: "Operating margin", unit: "%", pick: (y) => y.operating_margin_pct, criticalBelow: 0 },
  { label: "Days cash on hand", unit: " days", pick: (y) => y.days_cash_on_hand, criticalBelow: 30 },
  { label: "Days in A/R", unit: " days", pick: (y) => y.days_in_ar },
];

// Numbers first, chart as secondary reinforcement -- never chart-only. This
// product's whole trust model is exact, sourced figures, so the chart is a
// visual aid, not the source of truth.
export function TrendPanel({ hospital }: TrendPanelProps) {
  if (hospital.years.length === 0) {
    return <p className="dc-muted">No cost report data is available yet for this hospital.</p>;
  }

  const years = hospital.years.map((y) => y.fiscal_year);

  return (
    <div className="dc-trend-grid">
      {SERIES.map((series) => {
        const values = hospital.years.map(series.pick);
        const latest = values[values.length - 1];
        const isCritical =
          series.criticalBelow !== undefined && latest !== null && latest < series.criticalBelow;
        return (
          <div key={series.label} className="dc-trend-series">
            <div className="dc-trend-series-head">
              <span>{series.label}</span>
              <span className={isCritical ? "dc-trend-latest dc-tone-critical" : "dc-trend-latest"}>
                {formatMetric(latest, series.unit)}
              </span>
            </div>
            <TrendChart years={years} points={values} unit={series.unit} criticalBelow={series.criticalBelow} />
          </div>
        );
      })}
      {hospital.years.length < 3 && (
        <p className="dc-muted dc-small">
          Only {hospital.years.length} fiscal year{hospital.years.length === 1 ? "" : "s"} on file for
          this hospital -- a real reporting gap, not an error.
        </p>
      )}
    </div>
  );
}
