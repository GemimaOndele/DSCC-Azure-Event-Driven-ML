"""Environment configuration. No secret is ever read from this module."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MAX_CSV_BYTES = 1024 * 1024  # contract #14: stricter than the API's 8 MiB JSON cap
DEFAULT_MAX_BATCH_ROWS = 10_000  # same cap as POST /predict/batch
DEFAULT_API_CONNECT_TIMEOUT_S = 2.0
DEFAULT_API_READ_TIMEOUT_S = 10.0
DEFAULT_RECENT_LIMIT = 20
DEFAULT_MAX_DEQUEUE_COUNT = 5


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive, got {parsed}")
    return parsed


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive, got {parsed}")
    return parsed


@dataclass(frozen=True)
class Settings:
    """All tunable values, with safe local defaults (Azurite + local API)."""

    storage_account: str = ""
    model_api_url: str = "http://localhost:8000"
    cosmos_endpoint: str = ""
    dashboard_origin: str = ""
    max_csv_bytes: int = DEFAULT_MAX_CSV_BYTES
    max_batch_rows: int = DEFAULT_MAX_BATCH_ROWS
    api_connect_timeout_s: float = DEFAULT_API_CONNECT_TIMEOUT_S
    api_read_timeout_s: float = DEFAULT_API_READ_TIMEOUT_S
    recent_limit: int = DEFAULT_RECENT_LIMIT
    max_dequeue_count: int = DEFAULT_MAX_DEQUEUE_COUNT

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            storage_account=os.getenv("STORAGE_ACCOUNT", ""),
            model_api_url=os.getenv("MODEL_API_URL", "http://localhost:8000").rstrip("/"),
            cosmos_endpoint=os.getenv("COSMOS_ENDPOINT", ""),
            dashboard_origin=os.getenv("DASHBOARD_ORIGIN", "").rstrip("/"),
            max_csv_bytes=_int_env("MAX_CSV_BYTES", DEFAULT_MAX_CSV_BYTES),
            max_batch_rows=_int_env("MAX_BATCH_ROWS", DEFAULT_MAX_BATCH_ROWS),
            api_connect_timeout_s=_float_env(
                "API_CONNECT_TIMEOUT_SECONDS", DEFAULT_API_CONNECT_TIMEOUT_S
            ),
            api_read_timeout_s=_float_env(
                "API_READ_TIMEOUT_SECONDS", DEFAULT_API_READ_TIMEOUT_S
            ),
            recent_limit=_int_env("RECENT_LIMIT", DEFAULT_RECENT_LIMIT),
            max_dequeue_count=_int_env("MAX_DEQUEUE_COUNT", DEFAULT_MAX_DEQUEUE_COUNT),
        )
