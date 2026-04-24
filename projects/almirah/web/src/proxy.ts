import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { authCookieOptions, AUTH_COOKIE_DOMAIN } from "@/lib/supabase/cookies";

// Paths reachable without a session
const PUBLIC_PATHS = [/^\/signin$/, /^\/auth\//, /^\/api\/health$/];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((re) => re.test(pathname));
}

function redirectToSignin(request: NextRequest) {
  const signin = request.nextUrl.clone();
  signin.pathname = "/signin";
  signin.search = `?next=${encodeURIComponent(
    request.nextUrl.pathname + (request.nextUrl.search || ""),
  )}`;
  return NextResponse.redirect(signin);
}

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const url =
    process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Fail closed if Supabase isn't configured — treat missing env as
  // unauthenticated instead of silently serving every route.
  if (!url || !anonKey) {
    if (isPublic(request.nextUrl.pathname)) return supabaseResponse;
    return redirectToSignin(request);
  }

  const supabase = createServerClient(url, anonKey, {
    cookieOptions: authCookieOptions(),
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, { ...options, domain: AUTH_COOKIE_DOMAIN }),
        );
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;
  if (!user && !isPublic(pathname)) {
    return redirectToSignin(request);
  }

  if (user && pathname === "/signin") {
    const home = request.nextUrl.clone();
    home.pathname = "/";
    home.search = "";
    return NextResponse.redirect(home);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
