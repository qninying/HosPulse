import type { Status } from "./statusMapping";

type StatusPillProps = {
  status: Status;
  label: string;
};

// Single source of truth for status -> color. Color communicates status
// only, per the design brief -- nothing else on this dashboard uses color
// to mean anything else.
export function StatusPill({ status, label }: StatusPillProps) {
  return <span className={`dc-pill dc-pill-${status}`}>{label}</span>;
}
