FROM node:22-alpine

WORKDIR /app

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy dependency files first (cache layer)
COPY package*.json ./

# Install production deps
RUN npm ci --omit=dev

# Copy source
COPY . .

ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["node", "index.js"]
