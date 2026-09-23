import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Set both in frontend/.env.local."
  );
}

// Public anon key only — safe for server and client use. RLS on `hospitals`
// and `cost_report_years` allows public SELECT (see pipeline/schema.sql);
// this client never gets the service_role key.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
