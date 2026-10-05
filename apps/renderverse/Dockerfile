# Build from the repository root (npm workspaces need the root lockfile):
#   docker build -f apps/renderverse/Dockerfile -t renderverse .
FROM node:slim AS build

WORKDIR /usr/src/app

RUN apt-get update && apt-get upgrade -y

COPY package.json package-lock.json ./
COPY apps/renderverse/package.json ./apps/renderverse/

RUN chown -R node:node /usr/src/app

USER node

RUN npm install

ENV VITE_SECRET_ROOM_PASSWORD=VITE_SECRET_ROOM_PASSWORD
ENV VITE_PORT=VITE_PORT

COPY --chown=node:node apps/renderverse ./apps/renderverse

RUN npm run build --workspace apps/renderverse

EXPOSE 5173

FROM nginx:alpine3.21@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10

RUN apk update && apk upgrade --no-cache

COPY --from=build /usr/src/app/apps/renderverse/dist /usr/share/nginx/html

COPY apps/renderverse/nginx.conf /etc/nginx/conf.d/default.conf

COPY apps/renderverse/env.sh /docker-entrypoint.d/env.sh

RUN chmod +x /docker-entrypoint.d/env.sh
