# Ops: architecture

Ops is the private career workspace behind the Renderverse portfolio: job search, applications,
career documents, the portfolio site, inbox and calendar. The product brief is
[ops-product.md](ops-product.md); the screens come from the "Ops career workspace" design canvas.
This document records the decisions the build follows.

## Services

| Project                     | Role                                                      | Stack                                 |
| --------------------------- | --------------------------------------------------------- | ------------------------------------- |
| [ops-web](../apps/ops-web/) | The UI                                                    | React, Vite, Tailwind, TanStack Query |
| [ops-api](../apps/ops-api/) | System of record: every stored fact, document and version | FastAPI, SQLAlchemy, Alembic          |
| ezcareer-harness            | The agents (`career-consultant`, `job-finder`), over A2A  | Developed separately                  |
| artifact-service            | Renders documents to HTML and PDF                         | Developed separately                  |

- ops-api is the agents' client and owns all data: the agents prepare, ops-api stores, and the
  user sends and publishes. ops-web talks only to ops-api, including for the assistant panel.
- Both services run on one VM, reachable only inside the Tailscale tailnet: ops-api binds to
  `127.0.0.1` and is exposed with `tailscale serve`. Tailscale decides who can reach Ops, never
  who the user is; that is ops-api's job (see [Authentication](#authentication)).

## Authentication

ops-api owns sign-in, in `src/core/auth`, so every feature gets the user from `CurrentUserDep`.

- **Methods:** Google (OpenID Connect) and GitHub (OAuth 2), both with PKCE through Authlib, and
  email + password (Argon2id via pwdlib). A provider is offered once its client id and secret are
  set. There is no sign-up or reset by email: `python -m src.core.auth.cli set-password` sets a
  password on the server.
- **Who:** only emails in `auth.allowed_emails`. An SSO account signs in with its verified email;
  the first sign-in links it (`auth_identities`), so Google and GitHub with the same email are one
  user. Removing an email from the list ends that user's sessions on their next request.
- **Sessions:** a random token in the `ops_session` cookie (HttpOnly, SameSite=Lax, Secure on
  https, path `/ops-api`); `auth_sessions` stores only its SHA-256. A session expires after
  `auth.session_idle_days` without a request and can be revoked by deleting its row. No JWTs.
- **Guards:** state-changing requests from another site are rejected by `CSRFMiddleware`
  (`csrf.py`: `Sec-Fetch-Site`, falling back to `Origin`, as Go's `CrossOriginProtection` does); a wrong
  password and an unknown email get the same answer. Each email gets five password attempts per
  15-minute window, counted in `auth_sign_in_attempts` with one atomic upsert, so the limit holds
  across workers and against parallel bursts. The table is keyed by the email typed, not a user,
  so unknown emails are limited the same way; a successful sign-in or a new password clears it.
- **Local dev:** with `auth.enabled = false` every request acts as `auth.dev_email`, and ops-web
  hides sign-out.
- **Agents** (ezcareer-harness) will get their own API tokens with the `integrations/ezcareer`
  step; they never use the browser session.

## Data

- **Database:** Supabase Postgres over the session pooler; the root docker compose runs Postgres
  locally (`local` profile).
- **Users:** every table except `users` has a `user_id`, so other users can be added later; a test
  fails on a table without it. The request's user comes from `src/core/auth`.
- **Audit columns:** every feature table uses `AuditMixin` (`src/core/db/mixins.py`):
  `created_at`, `updated_at`, `created_by`, `updated_by`; a test fails on a feature table without
  it. `*_by` holds an actor string, `user:<uuid>`, `agent:<name>` or `system`, filled in on insert
  and update from the request's actor (`src/app/actor.py`, set by `current_user`). Only the
  latest change is kept, not a history. Auth tables keep just `created_at`.
- **Row level security:** every table has RLS enabled with `anon` / `authenticated` revoked.
  [`migrations/ext/rls.py`](../apps/ops-api/migrations/ext/rls.py) is an Alembic plugin, loaded
  in `env.py`: it adds `op.enable_rls()` / `op.disable_rls()` and an autogenerate comparator, so
  `alembic revision --autogenerate` writes `op.enable_rls("<table>")` for every new table, and for
  any existing table with RLS off, and `alembic check` fails until it is fixed. Migrations are
  never edited by hand for it. `tests/migrations/ext/test_rls.py` checks both against Postgres.
- **CI:** [migrations.yml](../.github/workflows/migrations.yml) has one job per service with
  migrations. The `ops-api` job runs a throwaway Postgres service container, applies the
  migrations, runs `alembic check`, downgrades and upgrades again, then runs the tests marked
  `postgres` (row level security). [tests.yml](../.github/workflows/tests.yml) runs every
  project's other tests.

## Feature-based architecture

Both services are split by feature, one per screen or capability, rather than by layer.

### ops-api

```
src/
├── main.py
├── app/            composition root: create_app, routers.py, container.py, models.py
├── core/           plumbing with no business rules: config, exceptions, logging, db/, auth/
├── integrations/   clients for outside services used by features (ezcareer, google, jsearch…)
└── features/<f>/
    ├── __init__.py     public API: the router and the service
    ├── router.py       HTTP only; routes take `<F>ServiceDep`, built on `SessionDep`
    ├── schemas.py      request and response models
    ├── service.py      the feature's operations
    ├── repository.py   database queries
    └── models.py       tables
```

Features: `dashboard` (reads other features, owns no tables), `jobs`, `applications`, `documents`,
`profile` (the facts agents and documents use), `portfolio` (media, releases, publishing),
`inbox`, `calendar`, `settings`, `assistant`. Tests mirror the layout under `tests/features/<f>/`.
A feature that outgrows single files turns a file into a package of the same name.

### ops-web

```
src/
├── app/            router (App.tsx), providers, shell/ (sidebar, page frame)
├── features/<f>/
│   ├── api/                 fetchers and types matching ops-api's schemas
│   ├── queries/             queryOptions and mutationOptions, with their query keys
│   ├── hooks/               hooks that call useQuery and useMutation with those options
│   ├── pages/               <Name>Page.tsx, one per route
│   ├── components/          the feature's components, flat
│   ├── lib/                 plain helpers and constants
│   ├── state/               zustand, only when the feature needs it
│   └── index.ts             public API
├── shared/         api/, components/, theme/, lib/
└── i18n/
```

### Rules

1. A feature imports another only through its public entry (`__init__.py`, `index.ts`).
2. Cross-feature calls in ops-api go through the other feature's service.
3. `core`, `integrations` and `shared` never import from `features`.
4. Only `app/` wires features together: routers, the DI container, routes and the sidebar.

### ops-web state

- **TanStack Query** holds everything from ops-api. Changes are mutations with optimistic updates
  that roll back on error; data is never copied into a store.
- **zustand** holds client state several components share: the theme, the assistant panel and its
  streaming reply, the documents editing draft.
- **The URL** holds tabs, filters and the selected item (`/jobs?tab=saved&posting=…`).

### Theme

`shared/theme/tokens.css` holds the design's light and dark palettes as Tailwind 4 theme
variables (`bg-panel`, `text-ink-3`, `border-hair`…); `html[data-theme="dark"]` swaps them. Light
is the default, dark is required, and the choice follows the system until the user picks one.

## Build order

1. Skeletons, app shell, theme, Settings, sign-in (done)
2. `profile` and the Portfolio screen
3. `documents`
4. `jobs` and `applications`
5. `dashboard`
6. `integrations/google`, then `inbox` and `calendar`

The assistant panel arrives with `integrations/ezcareer`. The first build of Ops is kept on the
local branch `archive/ops-v1` for reference.
