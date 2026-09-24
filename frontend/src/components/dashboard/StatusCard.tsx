import Link from "next/link";
import type { Status } from "./statusMapping";
import { STATUS_LABEL } from "./statusMapping";
import { StatusPill } from "./StatusPill";

type Metric = { label: string; value: string };

type StatusCardProps = {
  title: string;
  subtitle?: string;
  status: Status;
  primaryMetric?: Metric;
  supportingMetrics?: Metric[];
  lastUpdated?: string | null;
  href: string;
};

// The operational-overview card. One card per hospital: status readable at
// a glance, exact numbers underneath for the trust this product is built
// on, everything else behind the href drill-down rather than crammed in.
export function StatusCard({
  title,
  subtitle,
  status,
  primaryMetric,
  supportingMetrics,
  lastUpdated,
  href,
}: StatusCardProps) {
  return (
    <Link href={href} className={`dc-card dc-status-card dc-status-card-${status}`}>
      <div className="dc-card-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="dc-muted">{subtitle}</p>}
        </div>
        <StatusPill status={status} label={STATUS_LABEL[status]} />
      </div>
      <div className="dc-card-body">
        {primaryMetric && (
          <div className="dc-status-primary">
            <span className="dc-muted">{primaryMetric.label}</span>
            <strong>{primaryMetric.value}</strong>
          </div>
        )}
        {supportingMetrics && supportingMetrics.length > 0 && (
          <ul className="dc-status-supporting">
            {supportingMetrics.map((m) => (
              <li key={m.label}>
                <span className="dc-muted">{m.label}</span> {m.value}
              </li>
            ))}
          </ul>
        )}
        {lastUpdated && <p className="dc-timestamp">As of {lastUpdated}</p>}
      </div>
    </Link>
  );
}
