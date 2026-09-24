import type { SupabaseClient } from "@supabase/supabase-js";

export type LatestBriefing = {
  id: number;
  asOfDate: string;
  providerCcns: string[];
  body: string;
  generatedAt: string;
};

export type LatestBriefingOutcome =
  | { ok: true; briefing: LatestBriefing }
  | { ok: false; kind: "no_briefing" }
  | { ok: false; kind: "error"; error: string };

export async function getLatestBriefing(
  client: SupabaseClient,
  companyId: string
): Promise<LatestBriefingOutcome> {
  const { data, error } = await client
    .from("briefings")
    .select("id, as_of_date, provider_ccns, body, generated_at")
    .eq("company_id", companyId)
    .order("as_of_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    return { ok: false, kind: "error", error: error.message };
  }
  if (!data) {
    return { ok: false, kind: "no_briefing" };
  }

  return {
    ok: true,
    briefing: {
      id: data.id,
      asOfDate: data.as_of_date,
      providerCcns: (data.provider_ccns as string[]) ?? [],
      body: data.body,
      generatedAt: data.generated_at,
    },
  };
}
