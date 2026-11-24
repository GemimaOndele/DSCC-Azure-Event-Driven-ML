"""In-memory adapters for local/offline pipeline tests."""

from __future__ import annotations

from typing import Any


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

    def download(self, name: str) -> bytes:
        return self.containers["input"][name][0]

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

        blob_name = f"{name}.json"
        existing = self.containers["output"].get(blob_name)
        if existing and existing[1].get("idempotencykey") == idempotency_key:
            return False
        self.containers["output"][blob_name] = (
            json.dumps(payload).encode(),
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

    def exists(self, idempotency_key: str) -> bool:
        return idempotency_key in self.items

    def recent(self, limit: int) -> list[dict[str, Any]]:
        return sorted(
            self.items.values(), key=lambda item: item["timestamp"], reverse=True
        )[:limit]
