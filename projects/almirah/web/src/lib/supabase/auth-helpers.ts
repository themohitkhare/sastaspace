import { createClient } from "@/lib/supabase/server";

export async function getSessionUser() {
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    return user;
  } catch {
    // Missing Supabase env (local dev without .env.local). Treat as
    // unauthenticated so callers can respond with 401 instead of 500.
    return null;
  }
}

export async function isCurrentUserAdmin(): Promise<boolean> {
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user?.email) return false;

    const { data, error } = await supabase
      .from("admins")
      .select("email")
      .eq("email", user.email)
      .maybeSingle();

    if (error) return false;
    return !!data;
  } catch {
    return false;
  }
}
