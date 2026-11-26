# Getting started

ezcareer-harness keeps its tasks and checkpoints, including each conversation's thread, in Postgres by default (`stores = "postgres"` in `config.toml`). Read [the architecture overview](../architecture/overview.md#persistence-and-restarts) for what each store holds.

## Locally

1. Start the shared Postgres from the repository root: `docker compose up -d postgres`. It listens on `localhost:5432` with user, password and database `ops`, which `[database] url` in `config.toml` points at.
2. Run `pnpm nx run ezcareer-harness:migrate`. It runs the harness's Alembic migrations (`uv run alembic upgrade head`), which create the `ezcareer` schema when missing and the `task_owners` table, and keep their version in `ezcareer.alembic_version`. Run it again after you pull a new migration.
3. Run `pnpm nx run ezcareer-harness:dev`. At startup the harness creates the A2A and LangGraph tables when missing and takes over the tasks a stopped process left working.

To run without Postgres, change `EZCAREER_HARNESS_STORES` to `memory` in `.env`. A restart then loses every running turn and every conversation's thread, while ops-api still shows the messages.

## In Docker Compose

The harness's `docker-compose.yaml` waits for the `postgres` service and points `EZCAREER_HARNESS_DATABASE__URL` at `postgres:5432`, with the `POSTGRES_*` variables ops-api uses. Apply its migrations with:

```bash
docker compose run --rm --no-deps ezcareer-harness alembic upgrade head
```

## Migrations

To change the `task_owners` table, edit it in `src/infrastructure/stores/task_owners.py`, then run `uv run alembic revision --autogenerate -m "<what changed>"` in `apps/ezcareer-harness` and check the new file in `migrations/versions/`. Alembic manages only the tables in that module's `metadata`. a2a-sdk and LangGraph create their own.

## Tests and probes

Tests set `EZCAREER_HARNESS_STORES=memory` in `tests/conftest.py`, and `scripts/probe.py` sets it before it loads settings, so neither needs a database. Tests marked `postgres` run only when `EZCAREER_HARNESS_TEST_DATABASE_URL` points at a scratch database, for example `EZCAREER_HARNESS_TEST_DATABASE_URL=postgresql+psycopg://ops:ops@localhost:5432/<scratch> uv run pytest -m postgres`. Each test works in a schema of its own and drops it.
