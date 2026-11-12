FROM node:24-bookworm-slim AS renderverse-build

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

COPY apps/renderverse ./apps/renderverse

ARG VITE_EZBOT_API_URL=
ARG VITE_CHATBOT_ENABLED=false
ARG VITE_SECRET_ROOM_PASSWORD=
ARG VITE_PORTFOLIO_BUCKET_URL=
ARG VITE_PORTFOLIO_USER_ID=

RUN pnpm install --frozen-lockfile --ignore-scripts --filter renderverse \
    && pnpm --filter renderverse build

FROM nginxinc/nginx-unprivileged:stable-alpine AS renderverse

COPY apps/renderverse/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=renderverse-build /app/apps/renderverse/dist /usr/share/nginx/html

EXPOSE 8080
