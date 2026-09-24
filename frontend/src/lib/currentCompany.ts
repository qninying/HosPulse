import type { SupabaseClient } from "@supabase/supabase-js";

export type CurrentCompany = {
  id: string;
  name: string;
  providerCcns: string[];
};

export type CurrentCompanyOutcome =
  | { ok: true; company: CurrentCompany }
  | { ok: false; kind: "unauthenticated" }
  | { ok: false; kind: "no_company" }
  | { ok: false; kind: "error"; error: string };

// STORY-009: resolves the signed-in visitor to their real company via
// company_members -- never a hardcoded company id. RLS's own "see own
// membership" policy (user_id = auth.uid()) already scopes this select,
// so no .eq() is needed or even possible without a real session.
export async function getCurrentCompany(
  client: SupabaseClient
): Promise<CurrentCompanyOutcome> {
  const {
    data: { user },
    error: userError,
  } = await client.auth.getUser();

  if (userError || !user) {
    return { ok: false, kind: "unauthenticated" };
  }

  const { data: membership, error: membershipError } = await client
    .from("company_members")
    .select("company_id")
    .maybeSingle();

  if (membershipError) {
    return { ok: false, kind: "error", error: membershipError.message };
  }
  if (!membership) {
    return { ok: false, kind: "no_company" };
  }

  const { data: companyRow, error: companyError } = await client
    .from("companies")
    .select("id, name")
    .eq("id", membership.company_id)
    .maybeSingle();

  if (companyError) {
    return { ok: false, kind: "error", error: companyError.message };
  }
  if (!companyRow) {
    return { ok: false, kind: "no_company" };
  }

  const { data: hospitalRows, error: hospitalsError } = await client
    .from("company_hospitals")
    .select("provider_ccn")
    .eq("company_id", companyRow.id);

  if (hospitalsError) {
    return { ok: false, kind: "error", error: hospitalsError.message };
  }

  return {
    ok: true,
    company: {
      id: companyRow.id,
      name: companyRow.name,
      providerCcns: (hospitalRows ?? []).map((r) => r.provider_ccn),
    },
  };
}
