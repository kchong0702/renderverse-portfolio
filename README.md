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

## Getting Started

Run once after cloning:

```bash
npm install
npm run bootstrap
```

`bootstrap` creates the `.venv`, installs every Python workspace member with `uv sync --all-packages`, and copies each app's `.env.example` to `.env`.

## Common Tasks

```bash
npm run dev                  # run every app's dev target
npm run dev:renderverse      # web app only
npm run dev:ezbot            # chatbot only

npm run build
npm run lint                 # ESLint + Ruff
npm run test
npm run format               # Prettier + Ruff
npm run format:check

npm run docker:renderverse   # build the web image (context is the repo root)
```

Any target can be run directly with `npx nx run <project>:<target>`. Use `npx nx show project <project>` to list a project's targets, or `npx nx graph` to explore the workspace.

## Python

Python projects are members of the uv workspace declared in the root [pyproject.toml](pyproject.toml) and share the root `.venv` and `uv.lock`. To add a dependency to a member:

```bash
uv add --package ezbot <package>
uv add --package ezbot --dev <package>
```

A new Python app needs its own `pyproject.toml` and `project.json`, and must be listed under `[tool.uv.workspace].members`.
