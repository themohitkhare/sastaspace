# syntax=docker/dockerfile:1
# Build context for this Dockerfile is the REPO ROOT (set in
# infra/docker-compose.yml workers.build.context: ..). Audit N8: this
# replaces the previous `--no-frozen-lockfile` workaround with a frozen
# install from the workspace lockfile.
#
# Strategy: stage 1 (`workspace`) installs the full workspace deps with
# --frozen-lockfile so build can compile TypeScript using the dev deps that
# the lockfile resolves. Stage 2 (`prune`) re-runs `pnpm deploy --prod` to
# produce a self-contained pruned tree with prod-only deps for the runtime
# image. Stage 3 (final) is a tiny runtime image.
FROM node:22-alpine AS workspace
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
# Workspace metadata + lockfile.
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
# Workers + its in-workspace dep manifests.
COPY workers/package.json workers/tsconfig.json workers/
COPY packages/stdb-bindings/package.json packages/stdb-bindings/
COPY packages/typewars-bindings/package.json packages/typewars-bindings/
# Source for workers + the bindings packages it depends on.
COPY workers/src workers/src
COPY packages/stdb-bindings/src packages/stdb-bindings/src
COPY packages/typewars-bindings/src packages/typewars-bindings/src
# Frozen install of the workers package and its workspace deps. Includes dev
# deps so the build stage has TypeScript/vitest types.
RUN pnpm install --frozen-lockfile --filter @sastaspace/workers...

FROM workspace AS build
WORKDIR /repo/workers
RUN pnpm build

FROM workspace AS prune
WORKDIR /repo
# Self-contained prod-only tree at /tmp/pruned with workspace deps inlined.
RUN pnpm deploy --filter @sastaspace/workers --prod /tmp/pruned

FROM node:22-alpine
WORKDIR /app
# docker-cli for admin-collector's `docker logs --follow` shell-out
# (audit N18 tracks moving to dockerode streams).
RUN apk add --no-cache docker-cli
# N9: GPU stat CLI for admin-collector.readGpu(). taxila is AMD 7900 XTX so
# we need rocm-smi. The full ROCm package is huge; we only need the CLI
# binary, which lives in `rocm-smi-lib` on alpine edge community. The
# package may not be available in all alpine mirrors; readGpu() falls back
# gracefully when the binary is missing, and prod can host-bind
# /opt/rocm/bin/rocm-smi via compose volumes (documented in
# infra/README.md).
RUN apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/testing rocm-smi-lib || true
# Prod node_modules from the pruned tree (includes @sastaspace/stdb-bindings
# + @sastaspace/typewars-bindings — both shipping .ts source via package.json
# `main`, so we run via tsx at runtime instead of compiled .js).
COPY --from=prune /tmp/pruned/node_modules ./node_modules
# Workspace bindings + worker source (tsx compiles them on demand).
COPY --from=workspace /repo/packages/stdb-bindings ./packages/stdb-bindings
COPY --from=workspace /repo/packages/typewars-bindings ./packages/typewars-bindings
COPY --from=workspace /repo/workers/src ./src
COPY --from=workspace /repo/workers/tsconfig.json ./tsconfig.json
COPY --from=prune /tmp/pruned/package.json ./package.json
USER node
# tsx handles the .ts source at runtime; @sastaspace/stdb-bindings (workspace
# dep) exports .ts via package.json `main`, which tsx compiles on import.
CMD ["node", "--enable-source-maps", "--import", "tsx", "src/index.ts"]
