#!/usr/bin/env bash
# End-to-end verification for the local SastaSpace stack.
# Runs as a series of assertions; each prints PASS/FAIL and the reason.
# Exit code is 0 iff every check passed.
set -uo pipefail

cd "$(dirname "$0")/.."

PASS=0
FAIL=0
SECTION=""
RED=$'\e[31m'; GRN=$'\e[32m'; DIM=$'\e[2m'; NC=$'\e[0m'

section() { SECTION="$1"; printf '\n%s── %s ──%s\n' "$DIM" "$1" "$NC"; }
ok()  { printf '  %sPASS%s  %s\n' "$GRN" "$NC" "$1"; PASS=$((PASS+1)); }
bad() { printf '  %sFAIL%s  %s%s%s\n' "$RED" "$NC" "$1" "${2:+ — }" "${2:-}"; FAIL=$((FAIL+1)); }

# helper: run psql as postgres, capture stdout
psql_pg() {
  docker exec -i sastaspace-postgres psql -U postgres -d sastaspace -Atqc "$1" 2>&1
}

# ---- service health ---------------------------------------------------------
section "service health"

for url_name in "postgrest|http://localhost:3001/" "gotrue|http://localhost:9999/settings" "studio|http://localhost:3002/" "pg-meta|http://localhost:8080/tables" "landing|http://localhost:3000/" "gateway|http://localhost:8000/healthz" "gateway→auth|http://localhost:8000/auth/v1/settings" "gateway→rest|http://localhost:8000/rest/v1/projects?select=slug"; do
  name="${url_name%%|*}"; url="${url_name#*|}"
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo 000)
  case "$code" in
    200|301|302|307|308) ok "$name HTTP $code" ;;
    *) bad "$name" "$url returned $code" ;;
  esac
done

if psql_pg "SELECT 1" >/dev/null 2>&1 && [[ "$(psql_pg 'SELECT 1')" == "1" ]]; then
  ok "postgres accepts SQL queries"
else
  bad "postgres" "cannot run SELECT 1"
fi

# ---- DB schema --------------------------------------------------------------
section "database schema"

# roles
for role in anon authenticated service_role authenticator supabase_auth_admin; do
  if [[ "$(psql_pg "SELECT 1 FROM pg_roles WHERE rolname='$role'")" == "1" ]]; then
    ok "role '$role' exists"
  else
    bad "role '$role'" "missing"
  fi
done

# shared tables
for t in projects visits contact_messages admins; do
  count=$(psql_pg "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='$t'")
  if [[ "$count" == "1" ]]; then ok "table public.$t exists"; else bad "public.$t" "missing"; fi
done

# auth schema + helpers
if [[ "$(psql_pg "SELECT 1 FROM information_schema.schemata WHERE schema_name='auth'")" == "1" ]]; then
  ok "schema 'auth' exists"
else
  bad "schema 'auth'" "missing"
fi

for fn in "auth.jwt()" "auth.uid()" "auth.role()" "auth.email()" "public.is_admin()"; do
  proname="${fn#*.}"; proname="${proname%(*}"
  schemaname="${fn%%.*}"
  owner=$(psql_pg "SELECT r.rolname FROM pg_proc p JOIN pg_namespace n ON p.pronamespace=n.oid JOIN pg_roles r ON p.proowner=r.oid WHERE n.nspname='$schemaname' AND p.proname='$proname' LIMIT 1")
  if [[ -n "$owner" ]]; then
    ok "$fn exists (owner: $owner)"
  else
    bad "$fn" "missing"
  fi
done

# extensions
exts=$(psql_pg "SELECT string_agg(extname, ',' ORDER BY extname) FROM pg_extension WHERE extname IN ('pgcrypto','uuid-ossp','pgjwt','pg_trgm','unaccent','pg_stat_statements','vector','pg_graphql','pg_net')")
ok "extensions installed: $exts"

# RLS policies
rls_count=$(psql_pg "SELECT count(*)::text FROM pg_policies WHERE schemaname='public'")
if [[ "$rls_count" -ge "6" ]]; then
  ok "RLS policies on public: $rls_count"
else
  bad "RLS policies" "only $rls_count found, expected >=6"
fi

# admin seeded
if [[ "$(psql_pg "SELECT 1 FROM public.admins WHERE email='mohitkhare582@gmail.com'")" == "1" ]]; then
  ok "admin 'mohitkhare582@gmail.com' seeded"
else
  bad "admin seed" "mohitkhare582@gmail.com not in public.admins"
fi

# ---- seed test data ---------------------------------------------------------
section "seed data"

docker exec -i sastaspace-postgres psql -U postgres -d sastaspace >/dev/null <<'SQL'
INSERT INTO public.projects (slug, name, description, url, live_at) VALUES
  ('hello-world', 'Hello World',   'Smoke-test project.',              'https://hello-world.sastaspace.com', now()),
  ('draft-proj',  'Draft Project', 'Not yet published; should hide.',  'https://draft-proj.sastaspace.com',  NULL)
ON CONFLICT (slug) DO UPDATE SET live_at=excluded.live_at, description=excluded.description;
SQL
ok "seeded 1 live + 1 draft project"

# ---- PostgREST + RLS --------------------------------------------------------
section "PostgREST + RLS"

anon_resp=$(curl -s "http://localhost:3001/projects?select=slug")
if echo "$anon_resp" | grep -q '"slug":"hello-world"' && ! echo "$anon_resp" | grep -q '"slug":"draft-proj"'; then
  ok "anon sees live project, NOT draft (RLS works)"
else
  bad "anon RLS on projects" "response: $anon_resp"
fi

# service_role should see both via PostgREST (sign a fresh service_role JWT)
SERVICE_KEY=$(grep ^SERVICE_ROLE_KEY= .env | cut -d= -f2-)
svc_resp=$(curl -s -H "Authorization: Bearer $SERVICE_KEY" "http://localhost:3001/projects?select=slug")
if echo "$svc_resp" | grep -q "hello-world" && echo "$svc_resp" | grep -q "draft-proj"; then
  ok "service_role sees live + draft projects"
else
  bad "service_role on projects" "response: $svc_resp"
fi

# contact_messages: anon can insert
ins=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3001/contact_messages \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d '{"name":"Ver Bot","email":"bot@ver.test","message":"verify run","source_project":"landing"}')
if [[ "$ins" == "201" || "$ins" == "204" ]]; then
  ok "anon can INSERT contact_messages (HTTP $ins)"
else
  bad "anon insert" "contact_messages returned $ins"
fi

# contact_messages: anon cannot SELECT (RLS blocks; should be empty or 401/200 with no rows)
anon_read=$(curl -s "http://localhost:3001/contact_messages?select=email")
if [[ "$anon_read" == "[]" ]]; then
  ok "anon cannot read contact_messages (RLS)"
else
  bad "RLS on contact_messages" "anon got: $anon_read"
fi

# ---- GoTrue auth flow -------------------------------------------------------
section "GoTrue auth flow"

TEST_EMAIL="verify-$(date +%s)@local.dev"
TEST_PASS="VerifyPass123!"

signup=$(curl -s -X POST http://localhost:9999/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")
access_token=$(echo "$signup" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
user_id=$(echo "$signup" | python3 -c "import sys,json; print(json.load(sys.stdin).get('user',{}).get('id',''))")

if [[ -n "$access_token" && -n "$user_id" ]]; then
  ok "signup issued access_token (user_id=${user_id:0:8}...)"
else
  bad "signup" "no token. resp: $signup"
fi

# token carries role=authenticated
payload=$(echo "$access_token" | awk -F. '{print $2}' | python3 -c "import sys, base64; s=sys.stdin.read().strip(); s+='='*(-len(s)%4); import json; print(json.dumps(json.loads(base64.urlsafe_b64decode(s))))")
role=$(echo "$payload" | python3 -c "import sys,json; print(json.load(sys.stdin).get('role'))")
if [[ "$role" == "authenticated" ]]; then
  ok "issued JWT carries role=authenticated"
else
  bad "JWT role" "got: $role, payload=$payload"
fi

# token works with PostgREST
me=$(curl -s -H "Authorization: Bearer $access_token" "http://localhost:3001/projects?select=slug&limit=1")
if echo "$me" | grep -q "hello-world"; then
  ok "PostgREST accepts GoTrue-issued JWT"
else
  bad "JWT → PostgREST" "response: $me"
fi

# password login
login=$(curl -s -X POST "http://localhost:9999/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")
login_token=$(echo "$login" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
refresh_token=$(echo "$login" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")
if [[ -n "$login_token" && -n "$refresh_token" ]]; then
  ok "password grant issued access + refresh tokens"
else
  bad "password grant" "resp: $login"
fi

# refresh grant
refreshed=$(curl -s -X POST "http://localhost:9999/token?grant_type=refresh_token" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$refresh_token\"}")
new_access=$(echo "$refreshed" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
new_refresh=$(echo "$refreshed" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")
if [[ -n "$new_access" && -n "$new_refresh" ]]; then
  ok "refresh_token grant issues access + refresh tokens"
else
  bad "refresh grant" "resp: $(echo "$refreshed" | head -c 200)"
fi

# logout
lo=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:9999/logout \
  -H "Authorization: Bearer $new_access")
if [[ "$lo" == "204" || "$lo" == "200" ]]; then
  ok "logout HTTP $lo"
else
  bad "logout" "got $lo"
fi

# ---- admin allowlist --------------------------------------------------------
section "admin allowlist"

is_admin_self=$(psql_pg "
  SELECT (
    SELECT public.is_admin() FROM (SELECT set_config('request.jwt.claims','{\"email\":\"mohitkhare582@gmail.com\",\"role\":\"authenticated\"}'::text,true)) _
  )::text
")
case "$is_admin_self" in
  t|true) ok "is_admin() returns true for mohitkhare582@gmail.com" ;;
  *)      bad "is_admin (admin)" "got: $is_admin_self" ;;
esac

is_admin_other=$(psql_pg "
  SELECT (
    SELECT public.is_admin() FROM (SELECT set_config('request.jwt.claims','{\"email\":\"$TEST_EMAIL\",\"role\":\"authenticated\"}'::text,true)) _
  )::text
")
case "$is_admin_other" in
  f|false) ok "is_admin() returns false for random test user" ;;
  *)       bad "is_admin (non-admin)" "got: $is_admin_other" ;;
esac

# ---- landing SSR + routes ---------------------------------------------------
section "landing SSR"

home=$(curl -s http://localhost:3000/)
for needle in "SastaSpace" "Project Bank" "built and shipped" "Hello World" "Live projects"; do
  if echo "$home" | grep -q "$needle"; then
    ok "homepage contains '$needle'"
  else
    bad "homepage" "missing '$needle'"
  fi
done
if echo "$home" | grep -q "Draft Project"; then
  bad "homepage" "draft project leaked onto homepage!"
else
  ok "homepage hides draft project"
fi

for path in sign-in sign-up forgot-password contact; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:3000/$path")
  if [[ "$code" == "200" ]]; then
    ok "GET /$path HTTP $code"
  else
    bad "GET /$path" "got $code"
  fi
done

# /admin must redirect unauthenticated user to /sign-in
admin_code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/admin)
admin_loc=$(curl -s -I http://localhost:3000/admin | awk -F': ' 'tolower($1)=="location"{print $2}' | tr -d '\r')
if [[ "$admin_code" == "307" ]] && echo "$admin_loc" | grep -q "/sign-in"; then
  ok "GET /admin → 307 → $admin_loc"
else
  bad "/admin redirect" "code=$admin_code loc=$admin_loc"
fi

# ---- landing container reaches shared services by service DNS ---------------
section "container network (internal DNS)"

internal_gotrue=$(docker exec sastaspace-landing wget -qO- http://gotrue:9999/health 2>&1 | head -c 200)
if echo "$internal_gotrue" | grep -q "GoTrue"; then
  ok "landing → gotrue:9999 (internal DNS)"
else
  bad "internal DNS gotrue" "$internal_gotrue"
fi

internal_pgr=$(docker exec sastaspace-landing wget -qO- http://postgrest:3000/projects 2>&1 | head -c 200)
if echo "$internal_pgr" | grep -q "hello-world"; then
  ok "landing → postgrest:3000 (internal DNS)"
else
  bad "internal DNS postgrest" "$internal_pgr"
fi

# ---- full browser-like flow via the gateway --------------------------------
section "browser-like flow (through gateway)"

ADMIN_EMAIL="verify-admin-$(date +%s)@local.dev"
# Promote this email to admin for the duration of the check.
docker exec -i sastaspace-postgres psql -U postgres -d sastaspace >/dev/null <<SQL
INSERT INTO public.admins(email, note) VALUES ('$ADMIN_EMAIL','verify')
ON CONFLICT (email) DO NOTHING;
SQL

signup_gw=$(curl -s -X POST http://localhost:8000/auth/v1/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"AdminVerify123!\"}")
gw_token=$(echo "$signup_gw" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
if [[ -n "$gw_token" ]]; then
  ok "signup via gateway (/auth/v1/signup)"
else
  bad "signup via gateway" "resp: $(echo "$signup_gw" | head -c 200)"
fi

# CORS preflight from the landing origin
cors=$(curl -s -o /dev/null -w '%{http_code}' -X OPTIONS \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: POST' \
  http://localhost:8000/auth/v1/signup)
if [[ "$cors" == "204" ]]; then
  ok "gateway CORS preflight returns 204"
else
  bad "gateway CORS preflight" "got $cors"
fi

acao=$(curl -s -D - -o /dev/null -H 'Origin: http://localhost:3000' http://localhost:8000/auth/v1/settings | awk 'tolower($1)=="access-control-allow-origin:"{print $2}' | tr -d '\r' | head -n1)
if [[ "$acao" == "http://localhost:3000" ]]; then
  ok "gateway emits single ACAO=http://localhost:3000"
else
  bad "gateway CORS header" "ACAO='$acao'"
fi

# Signed-in admin can read admins via PostgREST through the gateway.
admin_rows=$(curl -s -H "Authorization: Bearer $gw_token" \
  "http://localhost:8000/rest/v1/admins?select=email")
if echo "$admin_rows" | grep -q "$ADMIN_EMAIL"; then
  ok "admin token reads public.admins via gateway"
else
  bad "admin via gateway" "rows: $admin_rows"
fi

# Cleanup the one-off admin.
docker exec -i sastaspace-postgres psql -U postgres -d sastaspace >/dev/null <<SQL
DELETE FROM public.admins WHERE email='$ADMIN_EMAIL';
SQL

# ---- summary ----------------------------------------------------------------
echo
echo "────────────────────────────"
if [[ "$FAIL" -eq 0 ]]; then
  printf '%sAll %d checks passed.%s\n' "$GRN" "$PASS" "$NC"
  exit 0
else
  printf '%s%d passed, %d failed.%s\n' "$RED" "$PASS" "$FAIL" "$NC"
  exit 1
fi
