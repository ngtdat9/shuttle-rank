export type AuthMode = "supabase" | "dev";

// Next.js inlines NEXT_PUBLIC_* into client bundles only for literal
// `process.env.NAME` reads; dynamic `process.env[name]` is undefined in the browser.
const AUTH_MODE = (process.env.NEXT_PUBLIC_AUTH_MODE ?? "").trim().toLowerCase();
const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").trim();
const SUPABASE_ANON_KEY = (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "").trim();

/**
 * `NEXT_PUBLIC_AUTH_MODE=dev` forces the development token form.
 * `supabase` forces email and password.
 * When unset, Supabase is used only if both public Supabase values are present.
 */
export function resolveAuthMode(): AuthMode {
  if (AUTH_MODE === "dev") return "dev";
  if (AUTH_MODE === "supabase") return "supabase";
  if (SUPABASE_URL && SUPABASE_ANON_KEY) return "supabase";
  return "dev";
}

export function hasSupabasePublicConfig(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}
