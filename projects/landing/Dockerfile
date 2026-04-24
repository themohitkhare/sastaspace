# Rails 8 multi-stage Dockerfile — Propshaft + Tailwind + Puma.
#
# Stage 1: build
#   - Installs Ruby gems and system deps
#   - Compiles Tailwind CSS
#   - Runs asset precompile (Propshaft sweeps fingerprinted assets into public/)
#
# Stage 2: run (final)
#   - Minimal image with compiled app
#   - Runs Puma as PID 1 via thruster (HTTP/2, asset caching, gzip)
#
# Target arch: amd64 (Ubuntu x86_64 prod host 192.168.0.37 / taxila).
#
# RAILS_MASTER_KEY is NOT needed at build time — we precompile assets with
# SECRET_KEY_BASE_DUMMY=1 so Rails skips the credentials check. The real
# master key is injected at runtime via Kamal's env.secret mechanism.

ARG RUBY_VERSION=4.0.3
FROM docker.io/library/ruby:${RUBY_VERSION}-slim AS base

WORKDIR /rails

# Runtime deps — libpq for pg gem, libvips for image_processing.
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
      curl \
      libpq5 \
      libvips \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives

# --- Build stage ---
FROM base AS build

ENV RAILS_ENV="production" \
    BUNDLE_DEPLOYMENT="1" \
    BUNDLE_PATH="/usr/local/bundle" \
    BUNDLE_WITHOUT="development:test"

# Build deps — native extensions need build-essential + libpq-dev + libyaml-dev.
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
      build-essential \
      git \
      libpq-dev \
      libyaml-dev \
      pkg-config \
    && rm -rf /var/lib/apt/lists /var/cache/apt/archives

# Install gems (production only).
COPY Gemfile Gemfile.lock ./
RUN bundle install && \
    rm -rf ~/.bundle/ "${BUNDLE_PATH}"/ruby/*/cache "${BUNDLE_PATH}"/ruby/*/bundler/gems/*/.git

# Copy application code.
COPY . .

# Compile Tailwind + Propshaft assets. SECRET_KEY_BASE_DUMMY=1 is the Rails 8
# convention that lets assets:precompile boot the app without a real master
# key — the runtime image receives RAILS_MASTER_KEY via Kamal env.secret.
RUN SECRET_KEY_BASE_DUMMY=1 bin/rails tailwindcss:build && \
    SECRET_KEY_BASE_DUMMY=1 bin/rails assets:precompile

# Precompile bootsnap cache to reduce boot times.
RUN bundle exec bootsnap precompile app/ lib/

# --- Runtime stage ---
FROM base AS final

ENV RAILS_ENV="production" \
    BUNDLE_DEPLOYMENT="1" \
    BUNDLE_PATH="/usr/local/bundle" \
    BUNDLE_WITHOUT="development:test" \
    RAILS_LOG_TO_STDOUT="1" \
    RAILS_SERVE_STATIC_FILES="1"

# Copy built gems + compiled app.
COPY --from=build /usr/local/bundle /usr/local/bundle
COPY --from=build /rails /rails

# Run as non-root user.
RUN groupadd --system --gid 1000 rails && \
    useradd rails --uid 1000 --gid 1000 --create-home --shell /bin/bash && \
    chown -R rails:rails db log storage tmp

USER 1000:1000

# Puma port (thruster proxies internally in Kamal).
EXPOSE 3000

# Boot via thruster → Puma.
ENTRYPOINT ["/rails/bin/thrust", "/rails/bin/rails", "server"]
