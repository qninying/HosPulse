import type { SupabaseClient } from "@supabase/supabase-js";

export type FlagStatus = "flagged" | "not_flagged" | "not_assessable";
// "no_data" is distinct from "not_assessable": no_data means the pipeline
// has never had monthly data to evaluate at all (this system's real
// starting state, since no operator has uploaded a real export yet);
// not_assessable means it was evaluated and genuinely couldn't tell.
export type SlippingStatus = "slipping" | "not_slipping" | "not_assessable" | "no_data";

export type EarlyWarningCriterion = {
  name: string;
  status: string;
  values: Record<string, unknown>;
};

export type HospitalOverviewRow = {
  provider_ccn: string;
  name: string | null;
  state: string;
  flagStatus: FlagStatus;
  flagFiscalYear: number | null;
  flagCriteria: EarlyWarningCriterion[];
  flagEvaluatedAt: string | null;
  slippingStatus: SlippingStatus;
};

export type DashboardHospitalsOutcome =
  | { ok: true; hospitals: HospitalOverviewRow[] }
  | { ok: false; kind: "error"; error: string };

// STORY-009: one row per hospital this company manages, merging the public
// hospitals table with the engine's own real flag/slipping output. A
// hospital this company manages but the engine has never flagged (no row
// in early_warning_flags at all) is "not_assessable", never silently
// dropped or shown as healthy.
export async function getDashboardHospitals(
  client: SupabaseClient,
  providerCcns: string[]
): Promise<DashboardHospitalsOutcome> {
  if (providerCcns.length === 0) {
    return { ok: true, hospitals: [] };
  }

  const [hospitalsRes, flagsRes, slippingRes] = await Promise.all([
    client.from("hospitals").select("provider_ccn, name, state").in("provider_ccn", providerCcns),
    client
      .from("early_warning_flags")
      .select("provider_ccn, status, as_of_fiscal_year, criteria, evaluated_at")
      .in("provider_ccn", providerCcns),
    client.from("slipping_hospital_alerts").select("provider_ccn, status").in("provider_ccn", providerCcns),
  ]);

  if (hospitalsRes.error) {
    return { ok: false, kind: "error", error: hospitalsRes.error.message };
  }
  if (flagsRes.error) {
    return { ok: false, kind: "error", error: flagsRes.error.message };
  }
  if (slippingRes.error) {
    return { ok: false, kind: "error", error: slippingRes.error.message };
  }

  const flagsByCcn = new Map(flagsRes.data?.map((f) => [f.provider_ccn, f]) ?? []);
  const slippingByCcn = new Map(slippingRes.data?.map((s) => [s.provider_ccn, s]) ?? []);

  const hospitals: HospitalOverviewRow[] = (hospitalsRes.data ?? []).map((h) => {
    const flag = flagsByCcn.get(h.provider_ccn);
    const slipping = slippingByCcn.get(h.provider_ccn);
    return {
      provider_ccn: h.provider_ccn,
      name: h.name,
      state: h.state,
      flagStatus: (flag?.status as FlagStatus) ?? "not_assessable",
      flagFiscalYear: flag?.as_of_fiscal_year ?? null,
      flagCriteria: (flag?.criteria as EarlyWarningCriterion[]) ?? [],
      flagEvaluatedAt: flag?.evaluated_at ?? null,
      slippingStatus: (slipping?.status as SlippingStatus) ?? "no_data",
    };
  });

  return { ok: true, hospitals };
}
