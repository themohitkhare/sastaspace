// Pin a stable auth cookie name that does not depend on the supabase URL.
//
// @supabase/ssr derives a default cookie name (e.g. `sb-localhost-auth-token`)
// from the Supabase project ref / hostname. Browser and server can see
// different URLs in our compose stack (browser → localhost:8000, server →
// gateway:8000), which would split the session across two cookies. Pinning a
// fixed name keeps them in sync.
export const AUTH_COOKIE_NAME = "sb-sastaspace-auth-token";

// Scope the auth cookie across the whole sastaspace apex so every subdomain
// (landing, almirah, future siblings) shares one session. On local dev the
// browser will reject any cookie with Domain=.sastaspace.com when the current
// host is localhost — that's fine because auth isn't wired locally. In
// production the deploy always runs on *.sastaspace.com hosts.
export const AUTH_COOKIE_DOMAIN = ".sastaspace.com";

export function authCookieOptions() {
  return { name: AUTH_COOKIE_NAME, domain: AUTH_COOKIE_DOMAIN };
}
