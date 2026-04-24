import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getSafeNext } from "@/lib/safe-next";
import { publicOrigin } from "@/lib/public-origin";

export async function GET(request: Request) {
  const origin = publicOrigin(request);
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const next = getSafeNext(searchParams.get("next"), origin);

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const destination = next.startsWith("http") ? next : `${origin}${next}`;
      return NextResponse.redirect(destination);
    }
  }

  return NextResponse.redirect(`${origin}/sign-in?error=auth_callback_failed`);
}
