FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS ops-api-build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

COPY apps/ops-api/pyproject.toml ./apps/ops-api/

COPY packages/document-schema ./packages/document-schema

RUN uv sync --frozen --no-dev --package ops-api

COPY apps/ops-api ./apps/ops-api

FROM python:3.13-slim-bookworm AS ops-api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    OPS_API_APP__HOST=0.0.0.0 \
    OPS_API_APP__PORT=8000

COPY --from=ops-api-build /app/.venv /app/.venv

COPY --from=ops-api-build /app/packages/document-schema /app/packages/document-schema

COPY --from=ops-api-build /app/apps/ops-api /app/apps/ops-api

RUN useradd --create-home --uid 10001 ops \
    && mkdir -p /app/apps/ops-api/.data \
    && chown ops /app/apps/ops-api/.data

USER ops
WORKDIR /app/apps/ops-api

EXPOSE 8000

CMD ["python", "-m", "src.main"]
