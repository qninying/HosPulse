import { supabase } from "./supabaseClient";

export type CostReportYear = {
  fiscal_year: number;
  operating_margin_pct: number | null;
  days_cash_on_hand: number | null;
  days_in_ar: number | null;
};

export type HospitalDetail = {
  provider_ccn: string;
  name: string | null;
  state: string;
  // Ascending by fiscal_year, at most 3 (the latest 3 on record). May be
  // fewer than 3 for a real hospital — CMS fiscal-year-end changes and
  // closures create genuine gaps; this is never padded to look complete.
  years: CostReportYear[];
};

export type HospitalDetailOutcome =
  | { ok: true; hospital: HospitalDetail }
  | { ok: false; kind: "not_found" }
  | { ok: false; kind: "error"; error: string };

export async function getHospitalTrends(
  providerCcn: string
): Promise<HospitalDetailOutcome> {
  const { data: hospitalRow, error: hospitalError } = await supabase
    .from("hospitals")
    .select("provider_ccn, name, state")
    .eq("provider_ccn", providerCcn)
    .maybeSingle();

  if (hospitalError) {
    return { ok: false, kind: "error", error: hospitalError.message };
  }
  if (!hospitalRow) {
    return { ok: false, kind: "not_found" };
  }

  const { data: yearRows, error: yearsError } = await supabase
    .from("cost_report_years")
    .select("fiscal_year, operating_margin_pct, days_cash_on_hand, days_in_ar")
    .eq("provider_ccn", providerCcn)
    .order("fiscal_year", { ascending: false })
    .limit(3);

  if (yearsError) {
    return { ok: false, kind: "error", error: yearsError.message };
  }

  const years = [...(yearRows ?? [])].sort(
    (a, b) => a.fiscal_year - b.fiscal_year
  );

  return {
    ok: true,
    hospital: {
      provider_ccn: hospitalRow.provider_ccn,
      name: hospitalRow.name,
      state: hospitalRow.state,
      years,
    },
  };
}

// Missing data is missing, never rendered as 0 or blank — REQ-005's
// "not assessable" rule (see pipeline/schema.sql) applies to display too.
export function formatMetric(value: number | null, unit: string): string {
  return value === null || value === undefined ? "not available" : `${value}${unit}`;
}

export const DATA_LAG_NOTE =
  "Figures come from CMS Hospital Cost Report filings. Hospitals typically file several months after a fiscal year ends, and CMS takes further time to process and publish the data, so the most recent year shown here may lag today by a year or more.";
