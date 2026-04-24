import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getSafeNext } from "@/lib/safe-next";
import { publicOrigin } from "@/lib/public-origin";

export async function GET(request: Request) {
  const origin = publicOrigin(request);
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const next = getSafeNext(searchParams.get("next"), origin);

  if (!code) {
    console.error("[auth/callback] missing code param");
    return NextResponse.redirect(
      `${origin}/sign-in?error=auth_callback_failed&reason=missing_code`,
    );
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    // Full detail server-side. The URL only gets a short reason code —
    // never the raw Supabase message (could leak PKCE internals).
    console.error("[auth/callback] exchange failed:", {
      status: error.status,
      code: error.code,
      message: error.message,
      name: error.name,
    });
    const reason = error.code || error.status?.toString() || "exchange_failed";
    return NextResponse.redirect(
      `${origin}/sign-in?error=auth_callback_failed&reason=${encodeURIComponent(reason)}`,
    );
  }

  console.info("[auth/callback] exchange succeeded for user:", data.user?.id);
  const destination = next.startsWith("http") ? next : `${origin}${next}`;
  return NextResponse.redirect(destination);
}
