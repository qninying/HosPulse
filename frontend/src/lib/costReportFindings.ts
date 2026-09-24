import type { SupabaseClient } from "@supabase/supabase-js";

export type CostReportFinding = {
  id: number;
  provider_ccn: string;
  fiscal_year: number;
  metric_name: string;
  cost_report_line: string;
  cost_report_value: number;
  ledger_value: number;
  relative_difference_pct: number;
  explanation: string;
  generated_at: string;
};

export type OpenFindingsOutcome =
  | { ok: true; findings: CostReportFinding[] }
  | { ok: false; kind: "error"; error: string };

// STORY-011 (.hospulse): the Cost Report Co-pilot's real output, surfaced
// per company. status='open' is the only state this story built -- a
// future specialist sign-off story adds the rest.
export async function getOpenCostReportFindings(
  client: SupabaseClient,
  providerCcns: string[]
): Promise<OpenFindingsOutcome> {
  if (providerCcns.length === 0) {
    return { ok: true, findings: [] };
  }

  const { data, error } = await client
    .from("cost_report_findings")
    .select(
      "id, provider_ccn, fiscal_year, metric_name, cost_report_line, cost_report_value, ledger_value, relative_difference_pct, explanation, generated_at"
    )
    .eq("status", "open")
    .in("provider_ccn", providerCcns)
    .order("generated_at", { ascending: false });

  if (error) {
    return { ok: false, kind: "error", error: error.message };
  }

  return { ok: true, findings: data ?? [] };
}
