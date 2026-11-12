FROM node:24-bookworm-slim AS ops-web-build

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

COPY packages/document-renderer ./packages/document-renderer

COPY apps/ops-web ./apps/ops-web

ARG VITE_OPS_API_URL=/ops-api/v1

RUN pnpm install --frozen-lockfile --ignore-scripts --filter ops-web... \
    && pnpm --filter ops-web build

FROM nginxinc/nginx-unprivileged:stable-alpine AS ops-web

COPY apps/ops-web/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=ops-web-build /app/apps/ops-web/dist /usr/share/nginx/html

EXPOSE 8080
