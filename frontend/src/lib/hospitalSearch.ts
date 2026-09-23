import { supabase } from "./supabaseClient";

export type HospitalSearchResult = {
  provider_ccn: string;
  name: string | null;
  state: string;
};

export type HospitalSearchOutcome =
  | { ok: true; hospitals: HospitalSearchResult[] }
  | { ok: false; error: string };

export function normalizeSearchTerm(raw: string | undefined): string {
  return (raw ?? "").trim();
}

// Case-insensitive partial match on name, since public users won't know a
// hospital's exact CMS-registered name string. Empty/whitespace terms are
// the caller's job to filter out before calling this (see page.tsx).
export async function searchHospitalsByName(
  term: string
): Promise<HospitalSearchOutcome> {
  const { data, error } = await supabase
    .from("hospitals")
    .select("provider_ccn, name, state")
    .ilike("name", `%${term}%`)
    .order("name", { ascending: true })
    .limit(25);

  if (error) {
    return { ok: false, error: error.message };
  }
  return { ok: true, hospitals: data ?? [] };
}
