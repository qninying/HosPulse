import type { HospitalOverviewRow } from "@/lib/companyHospitals";

// The one place this dashboard's generic status vocabulary maps onto real
// HosPulse states. "offline" is deliberately never produced -- there is no
// liveness/heartbeat concept for a hospital's data in this system, and
// inventing one would be exactly the kind of fake state this project
// refuses to ship. "loading" is never derived here either; it's a pure
// rendering-timing concern handled by loading.tsx.
export type Status = "critical" | "warning" | "ok" | "no_data";

export function deriveHospitalStatus(row: HospitalOverviewRow): Status {
  if (row.flagStatus === "not_assessable") {
    return "no_data";
  }
  if (row.flagStatus === "flagged") {
    return "critical";
  }
  // not_flagged: still worth a warning if the more recent monthly data
  // shows real decline the annual filing wouldn't catch until next year.
  if (row.slippingStatus === "slipping") {
    return "warning";
  }
  return "ok";
}

export const STATUS_LABEL: Record<Status, string> = {
  critical: "At risk",
  warning: "Watch",
  ok: "Stable",
  no_data: "No data yet",
};
