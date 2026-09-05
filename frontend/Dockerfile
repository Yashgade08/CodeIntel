# ──────────────────────────────────────────────────────────────────────
# CodeIntel Frontend — Multi-Stage Production Dockerfile
# ──────────────────────────────────────────────────────────────────────

# Stage 1: Build static assets with Node.js
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --frozen-lockfile || npm install

COPY . .

ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# ──────────────────────────────────────────────────────────────────────
# Stage 2: Serve static bundle via Nginx
FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
