FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS artifact-service-build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./

COPY apps/artifact-service/pyproject.toml ./apps/artifact-service/

COPY packages/document-schema ./packages/document-schema

RUN uv sync --frozen --no-dev --package artifact-service

COPY apps/artifact-service ./apps/artifact-service

FROM python:3.13-slim-bookworm AS artifact-service

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    ARTIFACT_SERVICE_APP__HOST=0.0.0.0 \
    ARTIFACT_SERVICE_APP__PORT=8000

COPY --from=artifact-service-build /app/.venv /app/.venv

COPY --from=artifact-service-build /app/packages/document-schema /app/packages/document-schema

COPY --from=artifact-service-build /app/apps/artifact-service /app/apps/artifact-service

RUN playwright install --with-deps chromium

RUN useradd --create-home --uid 10001 artifact

USER artifact
WORKDIR /app/apps/artifact-service

EXPOSE 8000

CMD ["python", "-m", "src.main"]
