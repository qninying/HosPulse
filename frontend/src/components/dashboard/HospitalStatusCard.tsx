import type { HospitalOverviewRow } from "@/lib/companyHospitals";
import { deriveHospitalStatus } from "./statusMapping";
import { StatusCard } from "./StatusCard";

type HospitalStatusCardProps = {
  hospital: HospitalOverviewRow;
};

const SLIPPING_LABEL: Record<string, string> = {
  slipping: "Slipping",
  not_slipping: "Not slipping",
  not_assessable: "Not assessable",
  no_data: "No monthly data yet",
};

export function HospitalStatusCard({ hospital }: HospitalStatusCardProps) {
  const status = deriveHospitalStatus(hospital);

  return (
    <StatusCard
      title={hospital.name ?? hospital.provider_ccn}
      subtitle={hospital.state}
      status={status}
      primaryMetric={
        hospital.flagFiscalYear
          ? { label: "Cost report status", value: `FY${hospital.flagFiscalYear}` }
          : undefined
      }
      supportingMetrics={[
        { label: "Monthly trend", value: SLIPPING_LABEL[hospital.slippingStatus] },
      ]}
      lastUpdated={
        hospital.flagEvaluatedAt
          ? new Date(hospital.flagEvaluatedAt).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })
          : null
      }
      href={`/dashboard/${hospital.provider_ccn}`}
    />
  );
}
