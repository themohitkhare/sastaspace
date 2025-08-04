FROM node:20-alpine

# Install dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Build for production
RUN npm run build

# Install serve to serve static files
RUN npm install -g serve

# Start production server
CMD ["serve", "-s", "dist", "-l", "3000"]
