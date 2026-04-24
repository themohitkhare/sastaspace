import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { publicOrigin } from "@/lib/public-origin";

export async function POST(request: NextRequest) {
  const origin = publicOrigin(request);

  // Reject cross-origin POSTs so a stored XSS on any other *.sastaspace.com
  // sibling can't force-logout via a drive-by same-site POST (the shared
  // Domain=.sastaspace.com cookie would otherwise be attached).
  const clientOrigin = request.headers.get("origin");
  if (clientOrigin && clientOrigin !== origin) {
    return new NextResponse("forbidden", { status: 403 });
  }

  const supabase = await createClient();
  await supabase.auth.signOut();
  return NextResponse.redirect(`${origin}/signin`, { status: 303 });
}
