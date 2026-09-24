import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabaseServerClient";
import { getCurrentCompany } from "@/lib/currentCompany";
import { getDashboardHospitals } from "@/lib/companyHospitals";
import { getHospitalTrends } from "@/lib/hospitalDetail";
import { getOpenCostReportFindings } from "@/lib/costReportFindings";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { Card } from "@/components/dashboard/Card";
import { StatusPill } from "@/components/dashboard/StatusPill";
import { STATUS_LABEL, deriveHospitalStatus } from "@/components/dashboard/statusMapping";
import { TrendPanel } from "@/components/dashboard/TrendPanel";
import { CostReportFindingsList } from "@/components/dashboard/CostReportFindingsList";

type PageProps = {
  params: Promise<{ ccn: string }>;
};

// The "Investigation -> Detailed data" layer of progressive disclosure:
// the exact triggering criteria (not just the status), this hospital's
// open findings, and its full trend -- everything the summary card on
// /dashboard deliberately left out.
export default async function DashboardHospitalPage({ params }: PageProps) {
  const { ccn } = await params;
  const client = await createSupabaseServerClient();
  const companyOutcome = await getCurrentCompany(client);

  if (!companyOutcome.ok) {
    return <EmptyState title="Not available" message="Sign in to view this hospital's details." />;
  }

  const { company } = companyOutcome;
  if (!company.providerCcns.includes(ccn)) {
    // RLS would already block the underlying data, but this is the honest
    // user-facing message rather than a raw empty-data render.
    return <EmptyState title="Not found" message="This hospital isn't managed by your company." />;
  }

  const [hospitalsOutcome, trendOutcome, findingsOutcome] = await Promise.all([
    getDashboardHospitals(client, [ccn]),
    getHospitalTrends(ccn),
    getOpenCostReportFindings(client, [ccn]),
  ]);

  if (!hospitalsOutcome.ok) {
    return <ErrorState message={hospitalsOutcome.error} />;
  }
  if (!findingsOutcome.ok) {
    return <ErrorState message={findingsOutcome.error} />;
  }

  const hospital = hospitalsOutcome.hospitals[0];
  if (!hospital) {
    return <EmptyState title="Not found" message="No data found for this hospital." />;
  }

  const status = deriveHospitalStatus(hospital);

  return (
    <main className="dc-dashboard">
      <p>
        <Link href="/dashboard">&larr; Back to dashboard</Link>
      </p>
      <div className="dc-titlebar">
        <div>
          <h1>{hospital.name ?? hospital.provider_ccn}</h1>
          <p className="dc-muted">{hospital.state}</p>
        </div>
        <StatusPill status={status} label={STATUS_LABEL[status]} />
      </div>

      <Card title="Early-warning criteria">
        {hospital.flagCriteria.length === 0 ? (
          <p className="dc-muted">No criteria recorded.</p>
        ) : (
          <ul className="dc-criteria-list">
            {hospital.flagCriteria.map((c) => (
              <li key={c.name}>
                <details>
                  <summary>
                    {c.name} &middot; {c.status}
                  </summary>
                  <pre>{JSON.stringify(c.values, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Financial trend">
        {trendOutcome.ok ? (
          <TrendPanel hospital={trendOutcome.hospital} />
        ) : (
          <p className="dc-muted">Trend data isn&apos;t available for this hospital right now.</p>
        )}
      </Card>

      <Card title="Possible missed reimbursement">
        <CostReportFindingsList
          findings={findingsOutcome.findings}
          hospitalNames={{ [hospital.provider_ccn]: hospital.name }}
        />
      </Card>
    </main>
  );
}
