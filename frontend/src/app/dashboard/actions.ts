"use server";

import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabaseServerClient";

// Closes the AI Employee Charter's largest named gap: a real specialist
// sign-off path for a Cost Report Co-pilot finding. Calls through the
// authenticated (cookie-session, RLS-bound) Supabase client, never the
// service-role key -- ADR-015's column-level GRANT plus the "company
// scoped decision" RLS policy are the real gate, this action only shapes
// the request; a client that skipped this form entirely would still be
// stopped at the database.
export async function decideCostReportFinding(formData: FormData): Promise<void> {
  const findingId = Number(formData.get("findingId"));
  const decision = String(formData.get("decision") ?? "");
  const note = String(formData.get("note") ?? "").trim();
  const returnTo = String(formData.get("returnTo") ?? "/dashboard");

  if (!findingId || (decision !== "confirmed" && decision !== "rejected")) {
    redirect(`${returnTo}?findingError=${encodeURIComponent("Invalid decision request.")}`);
  }

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect(`${returnTo}?findingError=${encodeURIComponent("Sign in required.")}`);
  }

  const { error } = await supabase
    .from("cost_report_findings")
    .update({
      status: decision,
      reviewed_by: user.id,
      reviewed_at: new Date().toISOString(),
      decision_note: note || null,
    })
    .eq("id", findingId)
    .eq("status", "open");

  if (error) {
    redirect(`${returnTo}?findingError=${encodeURIComponent(error.message)}`);
  }

  redirect(returnTo);
}
