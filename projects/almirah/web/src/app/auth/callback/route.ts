import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getSafeNext } from "@/lib/safe-next";
import { publicOrigin } from "@/lib/public-origin";

export async function GET(request: NextRequest) {
  const origin = publicOrigin(request);
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const next = getSafeNext(searchParams.get("next"), origin);

  if (!code) {
    return NextResponse.redirect(`${origin}/signin?error=missing_code`);
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    // Log the full Supabase error server-side; return a generic code in the
    // URL. Supabase messages can include PKCE/storage internals that aren't
    // useful to the user and shouldn't be reflected back into the browser.
    console.error("[auth/callback] exchange failed:", error.message);
    return NextResponse.redirect(`${origin}/signin?error=auth_callback_failed`);
  }

  const destination = next.startsWith("http") ? next : `${origin}${next}`;
  return NextResponse.redirect(destination);
}
