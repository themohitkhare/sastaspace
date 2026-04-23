// Pin a stable auth cookie name that does not depend on the supabase URL.
//
// @supabase/ssr derives a default cookie name (e.g. `sb-localhost-auth-token`)
// from the Supabase project ref / hostname. Browser and server can see
// different URLs in our compose stack (browser → localhost:8000, server →
// gateway:8000), which would split the session across two cookies. Pinning a
// fixed name keeps them in sync.
export const AUTH_COOKIE_NAME = "sb-sastaspace-auth-token";
