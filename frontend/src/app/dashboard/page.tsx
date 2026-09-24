import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabaseServerClient";
import { getCurrentCompany } from "@/lib/currentCompany";
import { getDashboardHospitals } from "@/lib/companyHospitals";
import { getLatestBriefing } from "@/lib/companyBriefing";
import { getOpenCostReportFindings } from "@/lib/costReportFindings";
import { getHospitalTrends } from "@/lib/hospitalDetail";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { Card } from "@/components/dashboard/Card";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { HospitalStatusCard } from "@/components/dashboard/HospitalStatusCard";
import { AttentionPanel } from "@/components/dashboard/AttentionPanel";
import { CostReportFindingsList } from "@/components/dashboard/CostReportFindingsList";
import { TrendPanel } from "@/components/dashboard/TrendPanel";

type PageProps = {
  searchParams: Promise<{ trend?: string }>;
};

export default async function DashboardPage({ searchParams }: PageProps) {
  const { trend } = await searchParams;
  const client = await createSupabaseServerClient();
  const companyOutcome = await getCurrentCompany(client);

  if (!companyOutcome.ok && companyOutcome.kind === "unauthenticated") {
    // Defense in depth -- middleware.ts already redirects unauthenticated
    // visitors away from /dashboard before this ever renders.
    return <EmptyState title="Sign in required" message="Please sign in to view your dashboard." />;
  }
  if (!companyOutcome.ok && companyOutcome.kind === "no_company") {
    return (
      <EmptyState
        title="No company linked yet"
        message="Your account isn't linked to a managed company yet. Contact your HosPulse admin to get set up."
      />
    );
  }
  if (!companyOutcome.ok) {
    return <ErrorState message={companyOutcome.error} />;
  }

  const { company } = companyOutcome;
  const [hospitalsOutcome, briefingOutcome, findingsOutcome] = await Promise.all([
    getDashboardHospitals(client, company.providerCcns),
    getLatestBriefing(client, company.id),
    getOpenCostReportFindings(client, company.providerCcns),
  ]);

  if (!hospitalsOutcome.ok) {
    return <ErrorState message={hospitalsOutcome.error} />;
  }
  if (!findingsOutcome.ok) {
    return <ErrorState message={findingsOutcome.error} />;
  }

  const hospitals = hospitalsOutcome.hospitals;
  const hospitalNames = Object.fromEntries(hospitals.map((h) => [h.provider_ccn, h.name]));

  const flaggedCount = hospitals.filter((h) => h.flagStatus === "flagged").length;
  const notAssessableCount = hospitals.filter((h) => h.flagStatus === "not_assessable").length;
  const slippingCount = hospitals.filter((h) => h.slippingStatus === "slipping").length;
  const allSlippingUnknown = hospitals.every((h) => h.slippingStatus === "no_data");

  const trendCcn =
    trend ?? hospitals.find((h) => h.flagStatus === "flagged")?.provider_ccn ?? hospitals[0]?.provider_ccn;
  const trendOutcome = trendCcn ? await getHospitalTrends(trendCcn) : null;

  return (
    <main className="dc-dashboard">
      <div className="dc-titlebar">
        <div>
          <h1>{company.name}</h1>
          <p className="dc-muted">{hospitals.length} hospital{hospitals.length === 1 ? "" : "s"} monitored</p>
        </div>
      </div>

      <section className="dc-kpi-row">
        <KpiCard
          label="At risk"
          value={flaggedCount}
          tone={flaggedCount > 0 ? "critical" : "ok"}
          href="#hospitals"
          tooltip="Hospitals the early-warning engine flagged: operating margin below 0%, days cash on hand below 30, or days in A/R rising two years in a row."
        />
        <KpiCard
          label="Slipping"
          value={allSlippingUnknown ? "No data yet" : slippingCount}
          tone={allSlippingUnknown ? "no_data" : slippingCount > 0 ? "warning" : "ok"}
          href="#hospitals"
          tooltip="Hospitals whose monthly ledger data shows real decline ahead of the annual cost report. Requires monthly exports to be uploaded."
        />
        <KpiCard
          label="Open findings"
          value={findingsOutcome.findings.length}
          tone={findingsOutcome.findings.length > 0 ? "warning" : "ok"}
          href="#findings"
          tooltip="Possible missed reimbursement items from the Cost Report Co-pilot, not yet reviewed."
        />
        <KpiCard label="Not assessable" value={notAssessableCount} tone="neutral" />
        <KpiCard label="Monitored" value={hospitals.length} tone="neutral" />
      </section>

      <section className="dc-grid-2">
        <Card title="This week's briefing">
          {briefingOutcome.ok ? (
            <AttentionPanel briefing={briefingOutcome.briefing} hospitalNames={hospitalNames} />
          ) : briefingOutcome.kind === "no_briefing" ? (
            <p className="dc-muted">No briefing has been generated for this company yet.</p>
          ) : (
            <p role="alert">We couldn&apos;t load the latest briefing. ({briefingOutcome.error})</p>
          )}
        </Card>

        <Card
          title="Trend"
          action={
            hospitals.length > 1 ? (
              <div className="dc-trend-picker">
                {hospitals.map((h) => (
                  <Link
                    key={h.provider_ccn}
                    href={`/dashboard?trend=${h.provider_ccn}`}
                    className={h.provider_ccn === trendCcn ? "dc-chip dc-chip-active" : "dc-chip"}
                  >
                    {h.name ?? h.provider_ccn}
                  </Link>
                ))}
              </div>
            ) : undefined
          }
        >
          {!trendOutcome ? (
            <p className="dc-muted">No hospitals to show a trend for.</p>
          ) : trendOutcome.ok ? (
            <TrendPanel hospital={trendOutcome.hospital} />
          ) : (
            <p className="dc-muted">Trend data isn&apos;t available for this hospital right now.</p>
          )}
        </Card>
      </section>

      <section id="hospitals">
        <h2>Managed hospitals</h2>
        {hospitals.length === 0 ? (
          <p className="dc-muted">No hospitals are assigned to your company yet.</p>
        ) : (
          <div className="dc-status-grid">
            {hospitals.map((h) => (
              <HospitalStatusCard key={h.provider_ccn} hospital={h} />
            ))}
          </div>
        )}
      </section>

      <section id="findings">
        <Card title="Possible missed reimbursement">
          <CostReportFindingsList findings={findingsOutcome.findings} hospitalNames={hospitalNames} />
        </Card>
      </section>
    </main>
  );
}
