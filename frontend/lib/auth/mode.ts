export type AuthMode = "supabase" | "dev";

function readEnv(name: string): string {
  const value = process.env[name];
  return typeof value === "string" ? value.trim() : "";
}

/**
 * `NEXT_PUBLIC_AUTH_MODE=dev` forces the development token form.
 * `supabase` forces email and password.
 * When unset, Supabase is used only if both public Supabase values are present.
 */
export function resolveAuthMode(): AuthMode {
  const explicit = readEnv("NEXT_PUBLIC_AUTH_MODE").toLowerCase();
  if (explicit === "dev") return "dev";
  if (explicit === "supabase") return "supabase";

  const url = readEnv("NEXT_PUBLIC_SUPABASE_URL");
  const anonKey = readEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  if (url && anonKey) return "supabase";
  return "dev";
}

export function hasSupabasePublicConfig(): boolean {
  return Boolean(
    readEnv("NEXT_PUBLIC_SUPABASE_URL") && readEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
  );
}
