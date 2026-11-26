"""In-memory adapters for local/offline pipeline tests."""

from __future__ import annotations

from typing import Any
from threading import Lock
from src.ports import StaleBlobVersionError


class InMemoryBlobStore:
    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.containers: dict[str, dict[str, tuple[bytes, dict[str, str]]]] = {
            "input": {},
            "output": {},
            "rejected": {},
        }
        for name, payload in (files or {}).items():
            self.containers["input"][name] = (payload, {})
        self.writes: list[tuple[str, str]] = []
        self.etags = {name: "0x8DC-A1" for name in (files or {})}
        self._lock = Lock()

    def download(self, name: str, *, etag: str) -> bytes:
        if self.etags.get(name) != etag.strip('"') or name not in self.containers["input"]:
            raise StaleBlobVersionError("Input version is no longer available")
        return self.containers["input"][name][0]

    def read_output(self, name: str, *, idempotency_key: str) -> dict[str, Any] | None:
        import json
        with self._lock:
            existing = self.containers["output"].get(f"{name}.{idempotency_key}.json")
            return json.loads(existing[0]) if existing else None

    def upload_rejected(self, name: str, reason: dict[str, Any]) -> str:
        import json

        blob_name = f"{name}.reason.json"
        self.containers["rejected"][blob_name] = (
            json.dumps(reason).encode(),
            {},
        )
        self.writes.append(("rejected", blob_name))
        return blob_name

    def upload_output(
        self, name: str, payload: dict[str, Any], *, idempotency_key: str
    ) -> bool:
        import json

        blob_name = f"{name}.{idempotency_key}.json"
        with self._lock:
            if blob_name in self.containers["output"]:
                return False
            self.containers["output"][blob_name] = (
                json.dumps(payload, allow_nan=False).encode(),
                {"idempotencykey": idempotency_key},
            )
            self.writes.append(("output", blob_name))
            return True


class FakeQueue:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, text: str) -> None:
        self.messages.append(text)


class InMemoryResultStore:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def upsert(self, metadata: dict[str, Any]) -> None:
        self.items[metadata["idempotencyKey"]] = metadata

    def exists(self, idempotency_key: str, *, file_name: str) -> bool:
        return idempotency_key in self.items

    def recent(self, limit: int) -> list[dict[str, Any]]:
        return sorted(
            self.items.values(), key=lambda item: item["timestamp"], reverse=True
        )[:limit]
