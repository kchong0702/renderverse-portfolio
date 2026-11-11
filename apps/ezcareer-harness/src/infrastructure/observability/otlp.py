from __future__ import annotations

from typing import Literal

from opentelemetry.sdk.resources import Resource

from src.core.config import ObservabilitySettings, Settings

Signal = Literal["traces", "metrics"]


def build_resource(settings: Settings) -> Resource:
    """Create resource shared by tracer and meter, injecting application metadata"""
    obs = settings.observability
    return Resource.create(
        {
            "service.name": obs.service_name,
            "service.version": settings.app.version,
            "deployment.environment": settings.app.env,
        }
    )


def build_endpoint(obs: ObservabilitySettings, signal: Signal) -> str:
    """Build the OTLP HTTP endpoint for a signal from the configured base endpoint"""
    endpoint = str(obs.otlp_endpoint).rstrip("/")
    suffix = f"/v1/{signal}"
    if not endpoint.endswith(suffix):
        endpoint = f"{endpoint}{suffix}"
    return endpoint


def parse_headers(obs: ObservabilitySettings) -> dict[str, str] | None:
    """Parse OTLP header from config"""
    if obs.otlp_headers is None:
        return None
    raw = obs.otlp_headers.get_secret_value().strip()
    if not raw:
        return None
    headers: dict[str, str] = {}
    for pair in raw.split(","):
        key, _, value = pair.partition("=")
        key, value = key.strip(), value.strip()
        if key:
            headers[key] = value
    return headers or None


__all__ = ["Signal", "build_endpoint", "build_resource", "parse_headers"]
