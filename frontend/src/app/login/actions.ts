"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabaseServerClient";

// STORY-009: passwordless sign-in. No password to manage, no signup form --
// the operator's email is provisioned in company_members ahead of time by
// an admin (the same real-world flow as the weekly briefing email list).
export async function sendMagicLink(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) {
    redirect("/login?error=missing_email");
  }

  const supabase = await createSupabaseServerClient();
  const origin = (await headers()).get("origin");

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${origin}/auth/callback`,
    },
  });

  if (error) {
    redirect(`/login?error=${encodeURIComponent(error.message)}`);
  }

  redirect(`/login?sent=1&email=${encodeURIComponent(email)}`);
}

// Fallback for the magic link: Gmail (and some other mail clients) pre-visit
// links in email for security scanning before the person ever clicks them,
// which silently burns a one-time sign-in link before it's used for real --
// confirmed live, not theoretical (the checkmark next to "Sign in" in a real
// test email was Gmail's own scanner marking it already-visited). A 6-digit
// code typed by hand can't be consumed by an automated scanner the way a
// clickable URL can, so this is the real fix, not the link itself retried.
export async function verifyOtpCode(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim();
  const token = String(formData.get("token") ?? "").trim();
  if (!email || !token) {
    redirect("/login?error=missing_email_or_code");
  }

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.verifyOtp({ email, token, type: "email" });

  if (error) {
    redirect(`/login?error=${encodeURIComponent(error.message)}&email=${encodeURIComponent(email)}`);
  }

  redirect("/dashboard");
}
