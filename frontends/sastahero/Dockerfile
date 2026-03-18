# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY sastahero/package.json sastahero/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY sastahero/ .

# Build the Vite app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config for SPA routing
COPY sastahero/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage to nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
