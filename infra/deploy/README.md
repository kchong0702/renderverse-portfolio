# Deployment

The backend runs from Docker images on one homelab VM, `blacksite`, which the blacksite-homelab repository prepares. renderverse is a static site on Cloudflare Pages. The databases are on Supabase, never on the VM: ops-api uses the `ops` schema and ezcareer-harness the `ezcareer` schema of one database.

The [Release](../../.github/workflows/release.yml) workflow does all of it.

## How a release ships

1. Every push to `main` builds the six VM images (ops-web, ops-api, ezcareer-harness, artifact-service, ezbot, ezbot-laya) and pushes them to private GHCR as `ghcr.io/<owner>/<image>:<commit sha>` and `:main`. ops-worker runs the ops-api image. A push to `main` never deploys.
2. The same run lets [release-please](https://github.com/googleapis/release-please) open or update a release PR. It reads the Conventional Commits since the last release, bumps the one version of the whole repository and writes `CHANGELOG.md`.
3. Merging the release PR tags the commit `vX.Y.Z` and creates a GitHub release. The run then adds the `vX.Y.Z` and `latest` tags to the images it built for that commit, without rebuilding, and deploys the release to the VM and to Pages.

The VM deploy reaches `blacksite` over Tailscale as the `deploy` user, copies the root `docker-compose.yaml`, every `apps/*/docker-compose.yaml`, the collector config, the Chromium seccomp profile, [deploy.sh](deploy.sh) and the `.env` files into `/srv/renderverse`, then runs `deploy.sh` once per step:

| Step                       | Command                                                                      |
| -------------------------- | ---------------------------------------------------------------------------- |
| `pull`                     | Log in to GHCR with the job's token, pull the release's images, log out      |
| `migrate ops-api`          | `alembic upgrade head` in a one-off ops-api container                        |
| `migrate ezcareer-harness` | The same for ezcareer-harness                                                |
| `up`                       | `docker compose up -d --remove-orphans`                                      |
| `health`                   | Poll every service's health endpoint for about 60 seconds                    |
| `prune`                    | Delete each image's local tags except the current and the previous release's |

The VM runs `docker compose -f docker-compose.yaml --profile apps`, which leaves out `docker-compose.override.yaml`, Postgres and renderverse. The job writes the `.env` files from the `production` environment's secrets and variables, chosen by name prefix (see [the list](#secrets-and-variables)), and adds `TAG` and `REGISTRY` to the root `.env`.

A failed migration stops the job before `up`, so the previous release keeps running. A failed health check rolls back on its own: `deploy.sh` puts back the `TAG` of the release ops-api was running before the deploy, starts it and fails the job. Only the images roll back; the compose files and `.env` settings stay the new release's. It never runs a down-migration. Pages deploys only after the VM deploy passes.

## Migrations must work with the previous release

A rollback runs the previous release's code against the new release's schema. So every migration must keep the previous release working:

- Add first. A new column is nullable or has a default; a new table is unused by old code.
- Remove later. Drop or rename a column only in a release after the one that stopped using it.

## Roll back by hand

Open **Actions**, then **Release**, then **Run workflow**, and enter a release tag such as `v1.2.0`. The run deploys that release to the VM and to Pages, without migrating down.

## One-time setup

- In **Settings**, then **Actions**, then **General**, allow GitHub Actions to create and approve pull requests, so release-please can open its PR.
- Create the `production` environment. Under **Deployment branches and tags**, choose **Selected branches and tags** and add the branch `main` and the tag pattern `v*`.
- Create a Tailscale OAuth client with the `auth_keys` write scope and the `tag:deploy` tag.
- blacksite-homelab's Terraform creates the Cloudflare Pages project `renderverse` and a token that can only deploy to Pages. Copy that token into `CLOUDFLARE_API_TOKEN`.
- After the first push to `main`, check that the six `ghcr.io/<owner>/*` packages are private.

## Secrets and variables

Create these in the `production` environment. Leave out the optional ones you don't use; a name is written to a `.env` file only when it is set.

| Name                                        | Kind     | Used for                                                     |
| ------------------------------------------- | -------- | ------------------------------------------------------------ |
| `TS_OAUTH_CLIENT_ID`                        | Secret   | Tailscale OAuth client                                       |
| `TS_OAUTH_SECRET`                           | Secret   | Tailscale OAuth client                                       |
| `DEPLOY_HOST`                               | Variable | The VM's tailnet name, `blacksite`                           |
| `CLOUDFLARE_API_TOKEN`                      | Secret   | Pages deploy                                                 |
| `CLOUDFLARE_ACCOUNT_ID`                     | Variable | Pages deploy                                                 |
| `DEPLOYMENT_ENV`                            | Variable | Root `.env`, the collector's `deployment.environment`        |
| `COLLECTOR_*`                               | Variable | Root `.env`, optional collector settings from `.env.example` |
| `OPS_API_DATABASE__URL`                     | Secret   | Supabase URL for ops-api                                     |
| `OPS_API_APP__ENV`                          | Variable | `prod`                                                       |
| `OPS_API_APP__CORS_ORIGIN`                  | Variable | `https://ops.kelvinchong.dev`                                |
| `OPS_API_AUTH__ENABLED`                     | Variable | `true`                                                       |
| `OPS_API_AUTH__WEB_URL`                     | Variable | `https://ops.kelvinchong.dev`                                |
| `OPS_API_AUTH__SECRET_KEY`                  | Secret   | Session signing key                                          |
| `OPS_API_AUTH__OIDC__GOOGLE__CLIENT_ID`     | Variable | Google sign-in                                               |
| `OPS_API_AUTH__OIDC__GOOGLE__CLIENT_SECRET` | Secret   | Google sign-in                                               |
| `OPS_API_AUTH__GITHUB__CLIENT_ID`           | Variable | GitHub sign-in                                               |
| `OPS_API_AUTH__GITHUB__CLIENT_SECRET`       | Secret   | GitHub sign-in                                               |
| `OPS_API_JSEARCH__ENCRYPTION_KEY`           | Secret   | Fernet key for stored JSearch keys                           |
| `OPS_API_GOOGLE__CLIENT_ID`                 | Variable | Gmail access                                                 |
| `OPS_API_GOOGLE__CLIENT_SECRET`             | Secret   | Gmail access                                                 |
| `OPS_API_GOOGLE__ENCRYPTION_KEY`            | Secret   | Fernet key for stored Google tokens                          |
| `OPS_API_GOOGLE__INBOX_QUERY`               | Variable | Optional Gmail search                                        |
| `OPS_API_STORAGE__R2__ACCOUNT_ID`           | Variable | R2 storage                                                   |
| `OPS_API_STORAGE__R2__BUCKET`               | Variable | R2 public bucket                                             |
| `OPS_API_STORAGE__R2__PRIVATE_BUCKET`       | Variable | R2 private bucket                                            |
| `OPS_API_STORAGE__R2__ACCESS_KEY_ID`        | Secret   | R2 storage                                                   |
| `OPS_API_STORAGE__R2__SECRET_ACCESS_KEY`    | Secret   | R2 storage                                                   |
| `OPS_API_PORTFOLIO__SITE_URL`               | Variable | Where renderverse is served                                  |
| `EZCAREER_HARNESS_DATABASE__URL`            | Secret   | Supabase URL for the harness                                 |
| `OPENAI_API_KEY`                            | Secret   | Harness models                                               |
| `ANTHROPIC_API_KEY`                         | Secret   | Harness models                                               |
| `AIGW_BASE_URL`                             | Variable | Harness gateway for the glm models                           |
| `AIGW_API_KEY`                              | Secret   | Harness gateway for the glm models                           |
| `ARTIFACT_SERVICE_LIBREOFFICE__COMMAND`     | Variable | Optional; the image's default is `soffice`                   |
| `EZBOT_APP__CORS_ORIGIN`                    | Variable | The renderverse origin                                       |
| `EZBOT_OBSERVABILITY__OTLP_HEADERS`         | Secret   | Optional exporter headers                                    |
| `GROQ_API_KEY`                              | Secret   | Ezbot model; set at least one of the four                    |
| `MISTRAL_API_KEY`                           | Secret   | Ezbot model                                                  |
| `GOOGLE_API_KEY`                            | Secret   | Ezbot model                                                  |
| `OPENROUTER_API_KEY`                        | Secret   | Ezbot model                                                  |
| `LAYA_THREADS`                              | Variable | Optional, default `2`                                        |
| `VITE_EZBOT_API_URL`                        | Variable | renderverse build                                            |
| `VITE_CHATBOT_ENABLED`                      | Variable | renderverse build                                            |
| `VITE_SECRET_ROOM_PASSWORD`                 | Secret   | renderverse build                                            |
| `VITE_PORTFOLIO_BUCKET_URL`                 | Variable | renderverse build                                            |
| `VITE_PORTFOLIO_USER_ID`                    | Variable | renderverse build                                            |

Each `.env` file gets the names with these prefixes:

| File                         | Prefixes                                                               |
| ---------------------------- | ---------------------------------------------------------------------- |
| `.env`                       | `COLLECTOR_`, `DEPLOYMENT_ENV`, plus `TAG` and `REGISTRY` from the job |
| `apps/ops-api/.env`          | `OPS_API_`                                                             |
| `apps/ezcareer-harness/.env` | `EZCAREER_HARNESS_`, `AIGW_`, `OPENAI_`, `ANTHROPIC_`                  |
| `apps/artifact-service/.env` | `ARTIFACT_SERVICE_`                                                    |
| `apps/ezbot-harness/.env`    | `EZBOT_`, `LAYA_`, `GROQ_`, `MISTRAL_`, `GOOGLE_`, `OPENROUTER_`       |

To add a setting, create a secret or variable with the right prefix; the workflow needs no change. Values are written single-quoted, so Compose reads `$` literally. A value can't contain a single quote or a newline; the job fails and names it.

## Local runs are unchanged

`pnpm run start` still builds nothing and runs every image locally, including Postgres and renderverse. Compose loads `docker-compose.override.yaml` on its own, which points ops-api, ops-worker and ezcareer-harness at the local `postgres` service. Postgres and renderverse have the `local` profile, which the VM never enables.
