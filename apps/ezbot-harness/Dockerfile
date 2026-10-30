FROM python:3.12-slim AS laya

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
    && pip install "laya[serve]==0.4.13"

RUN python -c "from laya import Router; Router(device='cpu').preload(['multilingual'])"

RUN useradd --create-home --uid 10001 laya && chown -R laya /models
USER laya

ENV HF_HUB_OFFLINE=1 \
    LAYA_DEVICE=cpu \
    LAYA_MODELS=multilingual \
    LAYA_DEFAULT_MODEL=multilingual \
    LAYA_MAX_LOADED=1 \
    LAYA_HOST=0.0.0.0 \
    LAYA_PORT=8000

EXPOSE 8000

CMD ["laya-serve"]

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS ezbot-build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/ezbot-harness/pyproject.toml ./apps/ezbot-harness/

RUN uv sync --frozen --no-dev --package ezbot-harness

COPY apps/ezbot-harness ./apps/ezbot-harness

FROM python:3.13-slim-bookworm AS ezbot

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    EZBOT_APP__HOST=0.0.0.0 \
    EZBOT_APP__PORT=8000

RUN useradd --create-home --uid 10001 ezbot

COPY --from=ezbot-build /app/.venv /app/.venv
COPY --from=ezbot-build /app/apps/ezbot-harness /app/apps/ezbot-harness

USER ezbot
WORKDIR /app/apps/ezbot-harness

EXPOSE 8000

CMD ["python", "-m", "src.main"]
