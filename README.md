# Renderverse

Nx monorepo for the Renderverse 3D portfolio and Ezbot, its chatbot.

## Workspace Structure

| App                              | Stack                   | Description                           |
| -------------------------------- | ----------------------- | ------------------------------------- |
| [renderverse](apps/renderverse/) | React / Three.js / Vite | 3D portfolio web app                  |
| [ezbot](apps/ezbot/)             | Python / LangGraph      | AI chatbot backend (work in progress) |

Shared libraries go in `packages/`.

## Prerequisites

| Tool    | Notes                                                               |
| ------- | ------------------------------------------------------------------- |
| Node.js | CI uses Node 24                                                     |
| uv      | Python dependency manager ([install](https://docs.astral.sh/uv/))   |
| Python  | 3.13+, downloaded automatically by `bootstrap` if none is installed |
| Docker  | Runs the OpenTelemetry collector                                    |

## Getting Started

Run once after cloning:

```bash
npm install
npm run bootstrap
```

`bootstrap` creates the `.venv`, installs every Python workspace member with `uv sync --all-packages`, and copies the root and each app's `.env.example` to `.env`. The root `.env` holds shared infrastructure settings (the OpenTelemetry collector); each app's `.env` holds settings only that app reads.

## Common Tasks

```bash
npm run dev                  # run every app's dev target
npm run dev:renderverse      # web app only
npm run dev:ezbot            # chatbot API only (http://localhost:8000/docs)

npm run build
npm run lint                 # ESLint + Ruff
npm run test
npm run format               # Prettier + Ruff
npm run format:check

npm run docker:renderverse   # build the web image (context is the repo root)

npm run infra:up             # start the root docker compose (OpenTelemetry collector)
npm run infra:logs
npm run infra:down
```

Any target can be run directly with `npx nx run <project>:<target>`. Use `npx nx show project <project>` to list a project's targets, or `npx nx graph` to explore the workspace.

## Python

Python projects are members of the uv workspace declared in the root [pyproject.toml](pyproject.toml) and share the root `.venv` and `uv.lock`. To add a dependency to a member:

```bash
uv add --package ezbot <package>
uv add --package ezbot --dev <package>
```

A new Python app needs its own `pyproject.toml` and `project.json`, and must be listed under `[tool.uv.workspace].members`.

## Chat

The web app talks to Ezbot over Server-Sent Events: it `POST`s each message, with the prior conversation as `history`, to `/ezbot/v1/chat`, and the response streams back `token` events followed by `done` or `error`. Stopping a reply aborts the request (`AbortController`); Ezbot sees the disconnect and cancels the LangGraph run.

To chat locally, set `VITE_CHATBOT_ENABLED=true` and `VITE_EZBOT_API_URL=http://localhost:8000` in `apps/renderverse/.env`, then `npm run dev`. Ezbot currently replies with a placeholder echo model ([model_factory.py](apps/ezbot/src/shared/model_factory.py)) until an LLM provider is wired in.

## Observability

Ezbot exports traces and metrics over OTLP/HTTP to the OpenTelemetry collector defined in the root [docker-compose.yaml](docker-compose.yaml), configured by [infra/otel-collector/config.yaml](infra/otel-collector/config.yaml). There are no backends yet, so the collector prints everything to its logs through the `debug` exporter. Set `COLLECTOR_EXPORTERS_DEBUG_VERBOSITY=detailed` in the root `.env` to see full spans and metrics.

Ezbot's settings come from [config.toml](apps/ezbot/config.toml), overridden by `.env` and environment variables prefixed with `EZBOT_`, using `__` for nested keys (e.g. `EZBOT_OBSERVABILITY__OTLP_ENDPOINT`).

The collector binds the standard OTLP ports (4317/4318). If another collector already holds them, change the `COLLECTOR_*_HOST_PORT` values in the root `.env` and point `EZBOT_OBSERVABILITY__OTLP_ENDPOINT` in `apps/ezbot/.env` at the new HTTP port.
