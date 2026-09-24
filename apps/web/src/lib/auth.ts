import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const localKey = "yom-awel.local-session";
let supabase: SupabaseClient | undefined;
export function cloudAuth() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) throw new Error("إعدادات تسجيل الدخول مش متاحة.");
  return (supabase ??= createClient(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  }));
}
export async function getToken(mode: string): Promise<string | null> {
  if (mode === "local") return localStorage.getItem(localKey);
  const { data, error } = await cloudAuth().auth.getSession();
  if (error) throw new Error("تعذّر استعادة الجلسة.");
  return data.session?.access_token ?? null;
}
export async function startSession(mode: string, api: string) {
  if (mode === "local") {
    const response = await fetch(api + "/api/v1/auth/local-session", {
      method: "POST",
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new Error("تعذّر بدء الجلسة. جرّب تاني بعد شوية.");
    const data = await response.json();
    localStorage.setItem(localKey, data.access_token);
    return data.access_token as string;
  }
  const { data, error } = await cloudAuth().auth.signInAnonymously();
  if (error || !data.session)
    throw new Error("تعذّر تسجيل الدخول. جرّب تاني بعد شوية.");
  return data.session.access_token;
}
export async function endSession(mode: string) {
  if (mode === "local") localStorage.removeItem(localKey);
  else {
    const { error } = await cloudAuth().auth.signOut({ scope: "local" });
    if (error) throw new Error("تعذّر تسجيل الخروج.");
  }
  sessionStorage.removeItem("yom-awel.pending");
}
