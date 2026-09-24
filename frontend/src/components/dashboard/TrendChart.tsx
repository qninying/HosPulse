type TrendChartProps = {
  years: number[];
  points: (number | null)[];
  unit: string;
  /** A value below this is the engine's own "triggered" threshold for this
   * metric (see pipeline/early_warning.py's OPERATING_MARGIN_THRESHOLD_PCT /
   * DAYS_CASH_ON_HAND_THRESHOLD_DAYS) -- drawn as a reference line so the
   * chart shows the same bar the product actually judges against, not an
   * arbitrary one. Omitted for metrics with no single-value threshold. */
  criticalBelow?: number;
};

const WIDTH = 640;
const HEIGHT = 150;
const PLOT_LEFT = 16;
const PLOT_RIGHT = 624;
const PLOT_TOP = 26;
const PLOT_BOTTOM = 94;
const FY_LABEL_Y = 118;

function formatValue(v: number, unit: string): string {
  return `${v}${unit}`;
}

// The first/last point sit right at the plot's horizontal edges, so
// centering their text on that same x would run it off the canvas --
// anchor those two inward instead, and leave interior points centered.
function edgeAwareAnchor(i: number, minX: number, maxX: number): "start" | "middle" | "end" {
  if (i === minX) return "start";
  if (i === maxX) return "end";
  return "middle";
}

// Hand-rolled inline SVG -- no charting library, matching this codebase's
// "no unnecessary dependencies" rule. Missing years are skipped entirely,
// never interpolated or drawn as zero -- a gap in the line is honest; a
// straight line through a fabricated zero is not. Numbers are drawn
// directly on the chart (every point, not just on hover) because this
// product's trust model is exact sourced figures first, chart second.
export function TrendChart({ years, points, unit, criticalBelow }: TrendChartProps) {
  const known = points
    .map((v, i) => (v === null ? null : { i, v }))
    .filter((p): p is { i: number; v: number } => p !== null);

  if (known.length === 0) {
    return (
      <div className="dc-chart-empty">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ width: "100%", height: "auto" }} aria-hidden="true">
          <text x={WIDTH / 2} y={HEIGHT / 2} textAnchor="middle" fontSize="12" fill="var(--dc-muted)">
            No data available
          </text>
        </svg>
      </div>
    );
  }

  const xs = points.map((_, i) => i);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const spanX = maxX - minX || 1;

  const knownValues = known.map((p) => p.v);
  const rangeValues = criticalBelow === undefined ? knownValues : [...knownValues, criticalBelow];
  const rawMin = Math.min(...rangeValues);
  const rawMax = Math.max(...rangeValues);
  const pad = (rawMax - rawMin) * 0.25 || Math.abs(rawMax) * 0.25 || 1;
  const minY = rawMin - pad;
  const maxY = rawMax + pad;
  const spanY = maxY - minY || 1;

  const plotWidth = PLOT_RIGHT - PLOT_LEFT;
  const plotHeight = PLOT_BOTTOM - PLOT_TOP;

  const xFor = (i: number) => PLOT_LEFT + ((i - minX) / spanX) * plotWidth;
  const yFor = (v: number) => PLOT_BOTTOM - ((v - minY) / spanY) * plotHeight;

  const linePoints = known.map(({ i, v }) => `${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`).join(" ");
  const lastKnown = known[known.length - 1];

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      style={{ width: "100%", height: "auto" }}
      role="img"
      aria-label="Fiscal-year trend chart"
    >
      <line x1={PLOT_LEFT} y1={PLOT_TOP} x2={PLOT_LEFT} y2={PLOT_BOTTOM} stroke="var(--dc-border)" strokeWidth="1" />
      <line x1={PLOT_LEFT} y1={PLOT_BOTTOM} x2={PLOT_RIGHT} y2={PLOT_BOTTOM} stroke="var(--dc-border)" strokeWidth="1" />

      {criticalBelow !== undefined && criticalBelow > minY && criticalBelow < maxY && (
        <>
          <line
            x1={PLOT_LEFT}
            y1={yFor(criticalBelow)}
            x2={PLOT_RIGHT}
            y2={yFor(criticalBelow)}
            stroke="var(--dc-critical)"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity="0.5"
          />
          <text x={PLOT_RIGHT} y={yFor(criticalBelow) - 4} textAnchor="end" fontSize="9" fill="var(--dc-critical)">
            {formatValue(criticalBelow, unit)} threshold
          </text>
        </>
      )}

      <polyline points={linePoints} fill="none" stroke="var(--dc-accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

      {known.map(({ i, v }) => {
        const isLast = i === lastKnown.i;
        const isCritical = criticalBelow !== undefined && v < criticalBelow;
        const dotColor = isLast && isCritical ? "var(--dc-critical)" : "var(--dc-accent)";
        const labelAbove = yFor(v) - PLOT_TOP > 16;
        return (
          <g key={i}>
            <circle cx={xFor(i)} cy={yFor(v)} r={isLast ? 4 : 3} fill={dotColor} stroke="var(--dc-panel)" strokeWidth="1.5" />
            <text
              x={xFor(i)}
              y={labelAbove ? yFor(v) - 10 : yFor(v) + 18}
              textAnchor={edgeAwareAnchor(i, minX, maxX)}
              fontSize="11"
              fontWeight={isLast ? 700 : 500}
              fill={isLast && isCritical ? "var(--dc-critical)" : "var(--dc-ink)"}
            >
              {formatValue(v, unit)}
            </text>
          </g>
        );
      })}

      {years.map((year, i) => (
        <text
          key={year}
          x={xFor(i)}
          y={FY_LABEL_Y}
          textAnchor={edgeAwareAnchor(i, minX, maxX)}
          fontSize="10"
          fill="var(--dc-muted)"
        >
          FY{year}
        </text>
      ))}
    </svg>
  );
}
