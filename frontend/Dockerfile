# ---- Dev (docker compose up — Vite dev server with HMR) ----
FROM node:22-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

EXPOSE 5173

CMD ["npm", "run", "dev"]

# ---- Production build (kept from branch chung) ----
FROM node:22-alpine AS builder

WORKDIR /app

# Relative URL keeps auth cookies first-party via nginx /api proxy.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
