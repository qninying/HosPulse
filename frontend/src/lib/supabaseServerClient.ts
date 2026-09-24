import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Set both in frontend/.env.local."
  );
}
const supabaseUrl: string = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey: string = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Anon key only, same as supabaseClient.ts -- the difference is this client
// is bound to the signed-in visitor's own session cookies, so auth.uid()
// resolves for real and RLS scopes every query to their own company. Built
// fresh per request (never a module singleton) since it's tied to that
// request's cookies. Server Components can only READ cookies -- the
// try/catch below is required because Next.js throws if a Server Component
// (as opposed to a Server Action or Route Handler) attempts to set one;
// middleware.ts is what actually persists a refreshed session cookie.
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        } catch {
          // Called from a Server Component render -- safe to ignore since
          // middleware.ts refreshes the session on every request anyway.
        }
      },
    },
  });
}
