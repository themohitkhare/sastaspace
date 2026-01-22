# Build stage
FROM oven/bun:1.3-alpine AS build

WORKDIR /app

# Copy shared directory first (needed for @shared alias)
COPY shared/ ./shared/

# Copy sastadice package files
COPY sastadice/package.json ./
COPY sastadice/bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy sastadice source files
COPY sastadice/ .

# Build the Vite app
RUN bun run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config for SPA routing
COPY sastadice/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage to nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx will start automatically with the base image
