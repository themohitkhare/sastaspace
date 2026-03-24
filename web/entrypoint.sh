#!/bin/sh
set -e

# Generate runtime env config for the browser.
# Only include NEXT_PUBLIC_* vars that client components need.
cat > /app/public/__env.js << EOF
window.__ENV__ = {
  NEXT_PUBLIC_BACKEND_URL: "${NEXT_PUBLIC_BACKEND_URL:-}",
  NEXT_PUBLIC_TURNSTILE_SITE_KEY: "${NEXT_PUBLIC_TURNSTILE_SITE_KEY:-}",
  NEXT_PUBLIC_ENABLE_TURNSTILE: "${NEXT_PUBLIC_ENABLE_TURNSTILE:-true}"
};
EOF

exec node server.js
