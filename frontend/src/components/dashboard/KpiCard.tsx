import Link from "next/link";
import type { Status } from "./statusMapping";

type KpiCardProps = {
  label: string;
  value: string | number;
  tone: Status | "neutral";
  context?: string;
  href?: string;
  tooltip?: string;
};

// Top-summary-layer primitive: one number, one tone, minimal decoration.
// Deliberately no icon set, no gradient -- the brief's own "avoid huge KPI
// numbers / excessive icons" rule.
export function KpiCard({ label, value, tone, context, href, tooltip }: KpiCardProps) {
  const body = (
    <>
      <div className="dc-kpi-label" title={tooltip}>
        {label}
      </div>
      <div className={`dc-kpi-value dc-tone-${tone}`}>{value}</div>
      {context && <div className="dc-kpi-context">{context}</div>}
    </>
  );

  if (href) {
    return (
      <Link href={href} className="dc-kpi-card dc-kpi-card-link">
        {body}
      </Link>
    );
  }
  return <div className="dc-kpi-card">{body}</div>;
}
