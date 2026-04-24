Template. Copy, rename, deploy.

## How to use

```bash
# Copy the template to a new project
rsync -a --exclude node_modules projects/_rails_template/ projects/<name>/

# Replace the landing placeholder throughout
find projects/<name> -type f \
  -exec sed -i.bak "s/landing/<name>/g" {} \; && \
  find projects/<name> -name "*.bak" -delete

# Install gems
cd projects/<name>
bundle install

# Start the dev server (requires POSTGRES_URL or local Postgres)
bin/dev
```

## Stack

- Rails 8.1 + Propshaft + import maps + Turbo + Stimulus
- Tailwind v4 with sastaspace brand tokens baked into CSS variables
- PostgreSQL (shared Supabase/Postgres instance, schema_search_path configurable)
- Solid Queue (Postgres-backed, no Redis)
- Kamal 2 deployment to 192.168.0.37

## Auth

- Rails 8 built-in session auth (signed HttpOnly cookie, `_sastaspace_session`)
- Google OAuth via `omniauth-google-oauth2` + `omniauth-rails_csrf_protection`
- Single callback URL: `https://sastaspace.com/auth/google/callback`

## AI client

`lib/anthropic_client.rb` wraps the `anthropic` gem pointed at the
cluster-local LiteLLM gateway (`LITELLM_BASE_URL`). Supports text and vision.

## Path routing

For sub-path projects (e.g. `/almirah`), set in `config/application.rb`:

```ruby
config.relative_url_root = "/almirah"
```

Landing mounts at root — no prefix needed.

## Deploy

```bash
# Update config/deploy.yml — replace <NAME>, <HOST>, <PATH_PREFIX>
kamal setup   # first deploy (provisions server, installs kamal-proxy)
kamal deploy  # subsequent deploys
```

See `design-log/006-rails-kamal-migration.md` for the full migration plan.
