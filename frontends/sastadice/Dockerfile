# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy shared directory first (needed for @shared alias)
COPY shared/ ./shared/

# Copy sastadice package files
COPY sastadice/package.json ./
COPY sastadice/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy sastadice source files
COPY sastadice/ .

# Build the Vite app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config for SPA routing
COPY sastadice/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx will start automatically with the base image
