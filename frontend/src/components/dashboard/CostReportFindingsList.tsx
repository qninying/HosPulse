import type { CostReportFinding } from "@/lib/costReportFindings";
import { decideCostReportFinding } from "@/app/dashboard/actions";

type CostReportFindingsListProps = {
  findings: CostReportFinding[];
  hospitalNames: Record<string, string | null>;
  returnTo: string;
};

// Native <details>/<summary> -- zero JS expand/collapse, matching this
// codebase's server-components-only architecture. The confirm/reject form
// below is the same pattern: a plain <form action={...}> server action,
// no client component needed for this either.
export function CostReportFindingsList({ findings, hospitalNames, returnTo }: CostReportFindingsListProps) {
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
            <form action={decideCostReportFinding} className="dc-finding-decision">
              <input type="hidden" name="findingId" value={f.id} />
              <input type="hidden" name="returnTo" value={returnTo} />
              <label htmlFor={`note-${f.id}`} className="dc-muted dc-small">
                Note (optional)
              </label>
              <input id={`note-${f.id}`} name="note" type="text" placeholder="Why this decision, if useful later" />
              <div className="dc-finding-decision-buttons">
                <button type="submit" name="decision" value="confirmed" className="dc-chip dc-chip-active">
                  Confirm
                </button>
                <button type="submit" name="decision" value="rejected" className="dc-chip">
                  Reject
                </button>
              </div>
            </form>
          </details>
        </li>
      ))}
    </ul>
  );
}
