FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS ezcareer-harness-build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

COPY apps/ezcareer-harness/pyproject.toml ./apps/ezcareer-harness/

COPY packages/document-schema ./packages/document-schema

RUN uv sync --frozen --no-dev --package ezcareer-harness

COPY apps/ezcareer-harness ./apps/ezcareer-harness

FROM python:3.13-slim-bookworm AS ezcareer-harness

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    EZCAREER_HARNESS_APP__HOST=0.0.0.0 \
    EZCAREER_HARNESS_APP__PORT=8000

COPY --from=ezcareer-harness-build /app/.venv /app/.venv

COPY --from=ezcareer-harness-build /app/packages/document-schema /app/packages/document-schema

COPY --from=ezcareer-harness-build /app/apps/ezcareer-harness /app/apps/ezcareer-harness

RUN useradd --create-home --uid 10001 ezcareer

USER ezcareer
WORKDIR /app/apps/ezcareer-harness

EXPOSE 8000

CMD ["python", "-m", "src.main"]
