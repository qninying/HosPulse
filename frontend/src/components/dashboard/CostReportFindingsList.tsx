import type { CostReportFinding } from "@/lib/costReportFindings";

type CostReportFindingsListProps = {
  findings: CostReportFinding[];
  hospitalNames: Record<string, string | null>;
};

// Native <details>/<summary> -- zero JS expand/collapse, matching this
// codebase's server-components-only architecture.
export function CostReportFindingsList({ findings, hospitalNames }: CostReportFindingsListProps) {
  if (findings.length === 0) {
    return <p className="dc-muted">No open findings right now.</p>;
  }

  return (
    <ul className="dc-findings-list">
      {findings.map((f) => (
        <li key={f.id}>
          <details>
            <summary>
              {hospitalNames[f.provider_ccn] ?? f.provider_ccn} &middot; {f.metric_name} &middot;{" "}
              {f.relative_difference_pct}% difference
            </summary>
            <p>
              <strong>{f.cost_report_line}</strong> (FY{f.fiscal_year}): cost report $
              {f.cost_report_value.toLocaleString()} vs. ledger ${f.ledger_value.toLocaleString()}.
            </p>
            <p>{f.explanation}</p>
          </details>
        </li>
      ))}
    </ul>
  );
}
