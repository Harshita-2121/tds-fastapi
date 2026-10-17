"""FastAPI service for the TDS config-precedence challenge."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent

# Layer 1: hardcoded defaults.
DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# Layer 4 fallback values reproduce the OS environment shown in the assignment.
# Actual APP_* environment variables on the hosting platform override these.
ASSIGNED_OS_ENV = {
    "APP_PORT": "8011",
    "APP_WORKERS": "3",
    "APP_DEBUG": "true",
    "APP_LOG_LEVEL": "warning",
    "APP_API_KEY": "key-assigned-secret",
}

TRUTHY = {"true", "1", "yes", "on"}


def config_key_from_env(name: str) -> str | None:
    """Map APP_* variables (and the .env alias NUM_WORKERS) to config keys."""
    if name == "NUM_WORKERS":
        return "workers"
    if name.startswith("APP_"):
        return name[4:].lower()
    return None


def coerce(key: str, value: Any) -> Any:
    """Apply the assignment's type rules to one configuration value."""
    if key in {"port", "workers"}:
        try:
            # int() also handles strings read from YAML, .env and query params.
            return int(value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"Configuration value for '{key}' must be an integer",
            )
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUTHY
    # log_level and every other setting are strings.
    return str(value)


def load_layered_config() -> dict[str, Any]:
    """Merge defaults -> YAML -> .env -> OS environment, low to high."""
    config: dict[str, Any] = dict(DEFAULTS)

    # Layer 2: environment-specific YAML.
    yaml_path = BASE_DIR / "config.development.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as stream:
            yaml_layer = yaml.safe_load(stream) or {}
        if isinstance(yaml_layer, dict):
            config.update(yaml_layer)

    # Layer 3: .env. APP_* names are normalized; NUM_WORKERS is an alias.
    env_path = BASE_DIR / ".env"
    dotenv_layer = dotenv_values(env_path) if env_path.exists() else {}
    for name, value in dotenv_layer.items():
        if value is None:
            continue
        key = config_key_from_env(name)
        if key is not None:
            config[key] = value

    # Layer 4: assigned OS values, then real process environment values.
    # The latter have priority because they are the actual runtime environment.
    os_layer = dict(ASSIGNED_OS_ENV)
    os_layer.update({key: value for key, value in os.environ.items() if key.startswith("APP_")})
    for name, value in os_layer.items():
        key = config_key_from_env(name)
        if key is not None:
            config[key] = value

    # Coerce all resolved values after the layers have been merged.
    return {key: coerce(key, value) for key, value in config.items()}


app = FastAPI(title="Effective Config API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "endpoint": "/effective-config"}


@app.get("/effective-config")
def effective_config(request: Request) -> JSONResponse:
    config = load_layered_config()

    # CLI-style parameters have the highest priority. Repeat `set` params are
    # accepted, and partition() preserves any additional '=' in a value.
    for item in request.query_params.getlist("set"):
        key, separator, raw_value = item.partition("=")
        if not separator or not key:
            continue
        if key == "NUM_WORKERS":
            key = "workers"
        elif key.startswith("APP_"):
            key = key[4:].lower()
        else:
            key = key.lower()
        config[key] = coerce(key, raw_value)

    # Never expose the real secret, regardless of which layer supplied it or
    # whether a caller tries to override api_key through `set`.
    config["api_key"] = "****"

    return JSONResponse(
        content=config,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store, max-age=0",
        },
    )
