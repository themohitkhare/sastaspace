# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy shared directory first (needed for @shared alias)
COPY shared/ ./shared/

# Copy sastaspace package files
COPY sastaspace/package.json ./
COPY sastaspace/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy sastaspace source files
COPY sastaspace/ .

# Build the Vite app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from builder stage to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx will start automatically with the base image
