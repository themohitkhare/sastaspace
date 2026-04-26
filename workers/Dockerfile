FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
COPY pnpm-lock.yaml* ./
# Lockfile lives at the monorepo root, not under workers/. The container build
# context is workers/, so the glob above is a no-op here. Use --no-frozen-lockfile
# so the skeleton image builds without copying the entire monorepo. Phase 1 may
# revisit this if reproducible CI builds become a constraint.
RUN corepack enable && corepack prepare pnpm@9 --activate && pnpm install --no-frozen-lockfile
COPY tsconfig.json ./
COPY src ./src
RUN pnpm build

FROM node:22-alpine
WORKDIR /app
RUN apk add --no-cache docker-cli
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
USER node
CMD ["node", "--enable-source-maps", "dist/index.js"]
