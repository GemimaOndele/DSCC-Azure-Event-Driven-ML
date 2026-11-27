"""Queue message contract and stable idempotency key (contract #14 §3/§5)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contract import CsvContractError, validate_blob_name, validate_size

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]")


class MessageError(ValueError):
    """The queue message is not a valid inference request."""


@dataclass(frozen=True)
class InferenceRequest:
    blobName: str
    etag: str
    size: int
    enqueuedAt: str

    @classmethod
    def create(cls, blob_name: str, etag: str, size: int, enqueued_at: str) -> "InferenceRequest":
        if not isinstance(blob_name, str) or not isinstance(enqueued_at, str):
            raise MessageError("blobName and enqueuedAt must be strings")
        if type(size) is not int:
            raise MessageError("size must be an integer")
        validate_blob_name(blob_name)
        validate_size(size, 1024 * 1024)
        if not isinstance(etag, str) or not etag or any(ord(c) < 32 or ord(c) == 127 for c in etag):
            raise MessageError("etag must be a non-empty string")
        try:
            datetime.fromisoformat(enqueued_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MessageError("enqueuedAt is not ISO-8601") from exc
        return cls(blobName=blob_name, etag=etag, size=size, enqueuedAt=enqueued_at)

    @classmethod
    def from_json(cls, raw: str | bytes) -> "InferenceRequest":
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise MessageError("Queue message is not valid JSON") from exc
        if not isinstance(data, dict):
            raise MessageError("Queue message must be a JSON object")
        expected = {"blobName", "etag", "size", "enqueuedAt"}
        if set(data) != expected:
            raise MessageError(
                f"Queue message must contain exactly {sorted(expected)}"
            )
        if not isinstance(data["size"], int) or isinstance(data["size"], bool):
            raise MessageError("size must be an integer")
        try:
            return cls.create(
                data["blobName"], data["etag"], data["size"], data["enqueuedAt"]
            )
        except CsvContractError as exc:
            raise MessageError(exc.reason) from exc

    def to_json(self) -> str:
        return json.dumps(
            {
                "blobName": self.blobName,
                "etag": self.etag,
                "size": self.size,
                "enqueuedAt": self.enqueuedAt,
            },
            separators=(",", ":"),
        )

    @property
    def idempotency_key(self) -> str:
        """Safe Cosmos `id`, stable across retries of the same blob version.

        Blob names and ETags may contain characters that are invalid or
        ambiguous in a Cosmos id, so a digest of both is appended.
        """
        digest = hashlib.sha256(
            f"{self.blobName}|{self.etag}".encode("utf-8")
        ).hexdigest()
        stem = _UNSAFE.sub("_", Path(self.blobName).stem)[:40]
        return f"{stem}-{digest[:16]}"


def rejection_reason(blob_name: str, reason: str) -> dict[str, str]:
    return {
        "blobName": blob_name,
        "reason": reason[:2000],
        "status": "rejected",
    }
