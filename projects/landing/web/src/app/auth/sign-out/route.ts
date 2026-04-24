import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { publicOrigin } from "@/lib/public-origin";

export async function POST(request: Request) {
  const origin = publicOrigin(request);

  // Reject cross-origin POSTs so stored XSS on any other *.sastaspace.com
  // sibling can't force-logout via the shared Domain=.sastaspace.com cookie.
  const clientOrigin = request.headers.get("origin");
  if (clientOrigin && clientOrigin !== origin) {
    return new NextResponse("forbidden", { status: 403 });
  }

  const supabase = await createClient();
  await supabase.auth.signOut();
  return NextResponse.redirect(`${origin}/`, { status: 303 });
}
