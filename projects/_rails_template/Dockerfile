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
# Target arch: arm64 (Apple Silicon / prod host 192.168.0.37).
#
# Build command:
#   docker build \
#     --build-arg RAILS_MASTER_KEY=$(cat config/master.key) \
#     -t localhost:32000/sastaspace-<NAME>:latest .

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

# RAILS_MASTER_KEY is passed as a build arg so Rails can decrypt credentials
# for the assets:precompile step. It does NOT appear in the final (runtime)
# image — the ARG scope ends at the build stage.
#
# Build with: docker build --build-arg RAILS_MASTER_KEY=$(cat config/master.key) …
# Kamal supplies this automatically via config/deploy.yml builder.secrets.
ARG RAILS_MASTER_KEY
ENV RAILS_MASTER_KEY=${RAILS_MASTER_KEY}

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

# Compile Tailwind + Propshaft assets.
RUN bin/rails tailwindcss:build && \
    bin/rails assets:precompile

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
