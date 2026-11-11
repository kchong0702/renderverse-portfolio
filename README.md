# Renderverse

Nx monorepo for the Renderverse 3D portfolio, Ezbot, its chatbot, and Ops, the private career workspace behind them, with the ezcareer harness that runs Ops' career agents.

## Workspace Structure

| App                                        | Stack                           | Description                                       |
| ------------------------------------------ | ------------------------------- | ------------------------------------------------- |
| [renderverse](apps/renderverse/)           | React / Three.js / Vite         | 3D portfolio web app                              |
| [ezbot-harness](apps/ezbot-harness/)       | Python / LangGraph              | AI chatbot backend (work in progress)             |
| [ops-web](apps/ops-web/)                   | React / Vite / Tailwind         | Ops UI: job search, documents, portfolio          |
| [ops-api](apps/ops-api/)                   | Python / FastAPI / SQLAlchemy   | Ops system of record                              |
| [ezcareer-harness](apps/ezcareer-harness/) | Python / LangGraph / deepagents | Ops' career agents and workflows, served over A2A |
| [artifact-service](apps/artifact-service/) | Python / FastAPI / Playwright   | Prints documents to PDF, converts Word résumés    |

| Package                                          | Stack             | Description                                                 |
| ------------------------------------------------ | ----------------- | ----------------------------------------------------------- |
| [document-schema](packages/document-schema/)     | Python / Pydantic | Résumé, CV and cover-letter model, edits and templates      |
| [document-renderer](packages/document-renderer/) | React / Paged.js  | Draws documents as paginated HTML, for ops-web and printing |

## Prerequisites

| Tool        | Notes                                                                |
| ----------- | -------------------------------------------------------------------- |
| Node.js     | CI uses Node 24                                                      |
| pnpm        | Version pinned in `packageManager`; `corepack enable` installs it    |
| uv          | Python dependency manager ([install](https://docs.astral.sh/uv/))    |
| Python      | 3.13+, downloaded automatically by `bootstrap` if none is installed  |
| Docker      | Runs Laya, the collector and the Ops Postgres, builds the app images |
| LibreOffice | Optional; artifact-service uses it to convert Word résumés           |

## Getting Started

Run once after cloning:

```bash
pnpm install
pnpm run bootstrap
```

`bootstrap` creates the `.venv`, installs every Python workspace member with `uv sync --all-packages`, and copies the root and each app's `.env.example` to `.env`. The root `.env` holds shared infrastructure settings (the OpenTelemetry collector); each app's `.env` holds settings only that app reads, including the ports and threads of its containers.

Then fill in the keys the apps need:

| File                         | Set                                                                                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/ezcareer-harness/.env` | `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`; `AIGW_BASE_URL` and `AIGW_API_KEY` for the OpenAI-compatible gateway that serves the glm models |
| `apps/ezbot-harness/.env`    | At least one free LLM key, e.g. `GROQ_API_KEY`                                                                                            |
| `apps/artifact-service/.env` | On macOS, `ARTIFACT_SERVICE_LIBREOFFICE__COMMAND=/Applications/LibreOffice.app/Contents/MacOS/soffice`                                    |
| `apps/renderverse/.env`      | `VITE_PORTFOLIO_USER_ID`, to show your published portfolio (see [Portfolio](#portfolio))                                                  |

## Common Tasks

```bash
pnpm run dev                  # run every app's dev target
pnpm run dev:renderverse      # web app only
pnpm run dev:ezbot-harness    # chatbot API on the host (http://localhost:8000/docs), starts the Laya container first
pnpm run dev:ops-web          # Ops UI only (http://localhost:5174)
pnpm run dev:ops-api          # Ops API on the host (http://localhost:8100/ops-api/docs), starts Postgres first
pnpm run dev:ops              # both Ops services, in one terminal
pnpm run migrate              # apply ops-api's database migrations
pnpm nx run ezcareer-harness:dev  # career agents (http://localhost:8200/ezcareer/docs)
pnpm nx run artifact-service:dev  # PDFs and Word conversion (http://localhost:8210/artifact-service/docs), builds document-renderer first

pnpm run build                # production artifacts: renderverse and ops-web dist, the app images
pnpm run preview:renderverse  # serve the built dist locally
pnpm run preview:ops-web      # serve the built Ops UI (http://localhost:4174), proxying to ops-api like dev
pnpm run start                # run the built images as the server does (collector, Laya, Ezbot, ezcareer-harness, artifact-service)
pnpm run lint                 # ESLint + Ruff
pnpm run test
pnpm run format               # Prettier + Ruff
pnpm run format:check

pnpm run infra:up             # start the OpenTelemetry collector for local dev
pnpm run infra:logs
pnpm run infra:down           # stop every container, including Postgres and those from pnpm run start
```

Any target can be run directly with `pnpm nx run <project>:<target>`. Use `pnpm nx show project <project>` to list a project's targets, or `pnpm nx graph` to explore the workspace.

## Python

Python projects are members of the uv workspace declared in the root [pyproject.toml](pyproject.toml) and share the root `.venv` and `uv.lock`. To add a dependency to a member:

```bash
uv add --package ezbot-harness <package>
uv add --package ezbot-harness --dev <package>
```

A new Python app needs its own `pyproject.toml` and `project.json`, and must be listed under `[tool.uv.workspace].members`.

## Chat

Ezbot is a LangChain agent ([graph.py](apps/ezbot-harness/src/features/agent/graph.py)) backed by free LLM APIs. [llm/factory.py](apps/ezbot-harness/src/features/llm/factory.py) builds the models listed under `[[llm.models]]` in [config.toml](apps/ezbot-harness/config.toml), in fallback order: Groq, Mistral, Gemini and OpenRouter are built-in presets, and `openai_compatible` reaches any other OpenAI-compatible provider. A model whose API key is missing is skipped; Ezbot refuses to start if none is left.

The system prompt lives in [prompts/ezbot.yaml](apps/ezbot-harness/src/features/agent/prompts/ezbot.yaml): metadata (`version`, `author`, `date`, `status`), the declared `input_variables`, and `system_prompt` written as a Jinja template, so variables can drive `{% if %}` and `{% for %}`. The file is loaded and compiled once at startup, with `compile` variables bound from settings (e.g. `intent_enabled`). A middleware renders it before every model call, reading each `runtime` variable from the agent state when a step has set it, otherwise from the request's `EzbotContext` (e.g. `today`). A template that uses an undeclared variable, or is missing one, fails at startup or render. Keep static instructions first and dynamic parts last, since providers cache the unchanged start of a prompt.

Each tab starts its own session with `POST /ezbot/v1/session`, which returns a session id and doubles as the frontend's online check. The first call also sets an HttpOnly cookie, kept until the browser closes and shared by all its tabs; a session only answers to its session id together with the cookie that created it. Opening another tab starts a new chat and leaves the others running. Ezbot keeps the last 20 turns of each session in memory as the model's context, so the web app only sends the new message; a session ends after 15 minutes without a message. At 2,000 live sessions new ones are refused with a 503 (the bot shows offline) rather than evicting anyone. Sessions live in process memory, so Ezbot runs a single worker.

`POST /ezbot/v1/chat` streams the reply as Server-Sent Events, in the style of OpenAI's Responses API: `response.output_text.delta` events with the text, an optional `response.intent`, then `response.completed`, `response.cancelled` or `response.failed`. Each event's JSON repeats its `type`. The reply is generated independently of the connection: every event has an `id`, the client reconnects to `GET /ezbot/v1/chat/stream` with `Last-Event-ID` if the connection drops, and `POST /ezbot/v1/chat/stop` stops a reply. Messages are rate-limited, counting every tab together: 10 per 10 minutes per cookie, 20 per 10 minutes per client IP, and 50 per rolling 24 hours per client IP (IPv6 counted per /64), answered with `429 RATE_LIMITED` or `429 DAILY_LIMIT`. Creating sessions is not limited. Limits live in memory, so a restart resets them.

While the reply streams, the [Laya](https://github.com/NandhaKishorM/laya) intent classifier decides whether the visitor asked to see skills, projects, about or contact; if confident, the `response.intent` event adds a button to the reply that flies the camera there. Laya runs as its own CPU-only container, started by `pnpm run dev:ezbot-harness` (its image builds once on first use); without it the chat still works, just without buttons.

To chat locally:

1. Put a free API key in `apps/ezbot-harness/.env`, e.g. `GROQ_API_KEY`.
2. `pnpm run infra:up` to start the collector, then `pnpm run dev:ezbot-harness`, which also starts Laya.
3. Set `VITE_CHATBOT_ENABLED=true` and `VITE_EZBOT_API_URL=http://localhost:8000` in `apps/renderverse/.env`, then `pnpm run dev:renderverse`.

In production the frontend and API must share a site (e.g. `example.com` and `api.example.com`) so the `SameSite=Lax` cookie is sent; set `EZBOT_APP__CORS_ORIGIN` to the frontend origin and `EZBOT_SESSION__COOKIE_SECURE=true`. Behind the Cloudflare Tunnel every request arrives from `cloudflared`, so [apps/ezbot-harness/docker-compose.yaml](apps/ezbot-harness/docker-compose.yaml) sets `EZBOT_RATE_LIMIT__CLIENT_IP_HEADER=cf-connecting-ip`; without it all visitors would share one IP's limits.

## Deployment

The frontend is built to `apps/renderverse/dist` for Cloudflare Pages. The backend runs on a server from Docker images: [apps/ezbot-harness/Dockerfile](apps/ezbot-harness/Dockerfile) builds both `ezbot` and `ezbot-laya` (one target each), and [apps/ezbot-harness/docker-compose.yaml](apps/ezbot-harness/docker-compose.yaml) runs them. The root [docker-compose.yaml](docker-compose.yaml) includes it, adds the collector, and puts every service on the `renderverse` network, where Ezbot reaches Laya and the collector by service name.

`pnpm run build` tags the images `:dev`; set `TAG` to tag them otherwise (e.g. a git SHA), and set the same `TAG` for `pnpm run start`, which runs the built images without building. Containers publish their ports on `127.0.0.1` only, for a Cloudflare Tunnel to reach.

## Ops

Ops runs locally against the `postgres` service of the root docker compose, which stands in for Supabase. It is in the `local` profile, so `pnpm run start` never runs it; `migrate` and `dev:ops-api` start it first.

```bash
pnpm run migrate
pnpm run dev:ops
```

The UI on http://localhost:5174 proxies `/ops-api` to ops-api, the same path `tailscale serve` routes on the VM. Locally auth is off and every request acts as `auth.dev_email` from [config.toml](apps/ops-api/config.toml), as an admin.

The agents and documents need two more services. ops-api calls the ezcareer harness (http://localhost:8200) for the assistant, job search, tailoring, résumé import and email, and artifact-service (http://localhost:8210) to export PDFs and list the templates. The harness also uses artifact-service, to read and print imported résumés. `pnpm run dev` starts everything; on its own, start them with `pnpm nx run ezcareer-harness:dev` and `pnpm nx run artifact-service:dev`.

### Portfolio

Only an admin sees Portfolio. With auth on, give your user the admin role in the database (`users.role = 'admin'`); locally the dev user is always an admin.

Publishing writes the release to `sites/<user_id>/release/current.json`, with its images and videos under `sites/<user_id>/media/`. With every `OPS_API_STORAGE__R2__*` variable set, it goes to the R2 public bucket, and uploads go to the private one; otherwise both stay under `apps/ops-api/.data/`. `OPS_API_PORTFOLIO__SITE_URL` is where the site is served (locally http://localhost:5173); without it, Portfolio hides the cover image and video buttons.

renderverse reads the current release straight from the bucket, never from ops-api. Set `VITE_PORTFOLIO_USER_ID` to your Ops user id, and `VITE_PORTFOLIO_BUCKET_URL` to the public bucket's address; leave it empty locally, where the dev server serves `/sites/...` from `apps/ops-api/.data/storage`. In production the bucket needs a CORS rule allowing GET from the site's domain.

### Sign-in

With `OPS_API_AUTH__ENABLED=true`, Ops needs a signed-in session: Google, GitHub, or an email and password. Only emails in `OPS_API_AUTH__ALLOWED_EMAILS` get in, and `OPS_API_AUTH__SECRET_KEY` must be set (e.g. `openssl rand -hex 32`); [apps/ops-api/.env.example](apps/ops-api/.env.example) lists every variable. Google and GitHub appear once their client id and secret are set, with this callback URL registered at the provider (`auth.web_url` is where ops-web is served):

```
<auth.web_url>/ops-api/v1/auth/google/callback
<auth.web_url>/ops-api/v1/auth/github/callback
```

There is no sign-up or password reset by email. Set a password on the machine running ops-api:

```bash
cd apps/ops-api && uv run python -m src.core.auth.cli set-password you@example.com
```

## Observability

Ezbot exports traces and metrics over OTLP/HTTP to the OpenTelemetry collector defined in the root [docker-compose.yaml](docker-compose.yaml), configured by [infra/otel-collector/config.yaml](infra/otel-collector/config.yaml). There are no backends yet, so the collector prints everything to its logs through the `debug` exporter. Set `COLLECTOR_EXPORTERS_DEBUG_VERBOSITY=detailed` in the root `.env` to see full spans and metrics.

Ezbot's settings come from [config.toml](apps/ezbot-harness/config.toml), overridden by `.env` and environment variables prefixed with `EZBOT_`, using `__` for nested keys (e.g. `EZBOT_OBSERVABILITY__OTLP_ENDPOINT`).

The collector binds the standard OTLP ports (4317/4318). If another collector already holds them, change the `COLLECTOR_*_HOST_PORT` values in the root `.env` and point `EZBOT_OBSERVABILITY__OTLP_ENDPOINT` in `apps/ezbot-harness/.env` at the new HTTP port.
