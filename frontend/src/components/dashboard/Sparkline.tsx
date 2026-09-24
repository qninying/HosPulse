type SparklineProps = {
  points: (number | null)[];
  width?: number;
  height?: number;
  stroke?: string;
};

// Hand-rolled inline SVG -- no charting library, matching this codebase's
// "no unnecessary dependencies" rule and the same technique already proven
// in project-blueprint/mockup.html. Missing years are skipped entirely,
// never interpolated or drawn as zero -- a gap in the line is honest; a
// straight line through a fabricated zero is not.
export function Sparkline({ points, width = 110, height = 32, stroke = "#13a39a" }: SparklineProps) {
  const known = points
    .map((v, i) => (v === null ? null : { i, v }))
    .filter((p): p is { i: number; v: number } => p !== null);

  if (known.length < 2) {
    return (
      <svg width={width} height={height} aria-hidden="true">
        <text x={4} y={height / 2 + 4} fontSize="11" fill="var(--dc-muted)">
          not enough data
        </text>
      </svg>
    );
  }

  const xs = known.map((p) => p.i);
  const ys = known.map((p) => p.v);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const pad = 3;

  const coords = known
    .map(({ i, v }) => {
      const x = pad + ((i - minX) / spanX) * (width - pad * 2);
      const y = height - pad - ((v - minY) / spanY) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} aria-hidden="true">
      <polyline points={coords} fill="none" stroke={stroke} strokeWidth="2" />
    </svg>
  );
}
