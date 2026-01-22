# Build stage
FROM oven/bun:1.3-alpine AS build

WORKDIR /app

# Copy shared directory first (needed for @shared alias)
COPY shared/ ./shared/

# Copy sastaspace package files
COPY sastaspace/package.json ./
COPY sastaspace/bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy sastaspace source files
COPY sastaspace/ .

# Build the Vite app
RUN bun run build

# Production stage
FROM nginx:alpine

# Copy built files from builder stage to nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx will start automatically with the base image
