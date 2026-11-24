"""Interfaces used by the orchestration layer.

The Azure implementations live in ``azure_clients.py``. In-memory versions in
``tests/fakes.py`` let the whole pipeline be exercised locally with Azurite or
no cloud at all.
"""

from __future__ import annotations

from typing import Any, Protocol


class BlobStore(Protocol):
    def download(self, name: str) -> bytes: ...

    def upload_rejected(self, name: str, reason: dict[str, Any]) -> str: ...

    def upload_output(
        self, name: str, payload: dict[str, Any], *, idempotency_key: str
    ) -> bool:
        """Return True when a new blob was written, False when already present."""
        ...


class QueueSender(Protocol):
    def send_message(self, text: str) -> None: ...


class ResultStore(Protocol):
    def upsert(self, metadata: dict[str, Any]) -> None: ...

    def exists(self, idempotency_key: str) -> bool: ...

    def recent(self, limit: int) -> list[dict[str, Any]]: ...
