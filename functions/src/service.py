"""Orchestration shared by the three Functions (no Azure SDK imports)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote, urlparse

from .api_client import (
    InferenceClient,
    InferenceError,
    PermanentInferenceError,
    TransientInferenceError,
    validate_batch_response,
)
from .config import Settings
from .contract import CsvContractError, parse_csv, validate_blob_name, validate_size
from .messages import InferenceRequest, MessageError, rejection_reason
from .ports import BlobStore, QueueSender, ResultStore, StaleBlobVersionError

LOGGER = logging.getLogger("dscc.pipeline")


class RetryableWorkerError(RuntimeError):
    """Raised to the Functions host so the queue retries (then poison)."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def blob_name_from_event(data: dict[str, Any]) -> str:
    """Accept both Event Grid's event URL and an explicit blobName field."""
    name = data.get("blobName")
    if isinstance(name, str) and name:
        return unquote(name)
    url = data.get("url")
    if isinstance(url, str) and url:
        return unquote(urlparse(url).path.lstrip("/").split("/", 1)[-1])
    raise MessageError("Event Grid event has neither blobName nor url")


def dispatch(
    event_data: dict[str, Any],
    *,
    settings: Settings,
    blobs: BlobStore,
    queue: QueueSender,
) -> dict[str, Any]:
    """Validate the uploaded CSV and enqueue one inference request."""
    try:
        blob_name = blob_name_from_event(event_data)
        validate_blob_name(blob_name)
        size = int(event_data.get("contentLength", event_data.get("size", 0)))
        validate_size(size, settings.max_csv_bytes)
        etag = event_data.get("etag") or event_data.get("eTag") or ""
        if not isinstance(etag, str) or not etag:
            raise MessageError("Event Grid event has no etag")
        data = blobs.download(blob_name, etag=etag)
        if len(data) != size and size:
            raise CsvContractError(
                f"Declared size {size} does not match downloaded size {len(data)}"
            )
        rows = parse_csv(data, settings=settings, blob_name=blob_name)
        message = InferenceRequest.create(
            blob_name, str(etag), len(data), _utc_now()
        )
        queue.send_message(message.to_json())
    except StaleBlobVersionError:
        return {"status": "superseded"}
    except (CsvContractError, MessageError, ValueError) as exc:
        reason = exc.reason if isinstance(exc, CsvContractError) else "Invalid event metadata"
        safe_name = "unknown.csv"
        try:
            candidate = locals().get("blob_name", "")
            validate_blob_name(candidate)
            safe_name = candidate
        except CsvContractError:
            pass
        blobs.upload_rejected(safe_name, rejection_reason(safe_name, reason))
        LOGGER.warning("CSV rejected", extra={"reason": reason[:300]})
        return {"status": "rejected", "reason": reason}

    LOGGER.info(
        "CSV queued", extra={"blobName": blob_name, "rows": len(rows), "size": len(data)}
    )
    return {"status": "queued", "blobName": blob_name, "rows": len(rows)}


def process(
    message_json: str | bytes,
    *,
    settings: Settings,
    blobs: BlobStore,
    api: InferenceClient,
    results: ResultStore,
) -> dict[str, Any]:
    """Run one queue message. Permanent errors reject, transient errors retry."""
    try:
        request = InferenceRequest.from_json(message_json)
    except MessageError as exc:
        # Invalid queue envelope is not a transient service failure.
        blobs.upload_rejected("unknown.csv", rejection_reason("unknown.csv", "Invalid queue message"))
        return {"status": "rejected", "reason": "Invalid queue message"}
    key = request.idempotency_key
    if results.exists(key, file_name=request.blobName):
        LOGGER.info("Duplicate delivery ignored", extra={"idempotencyKey": key})
        return {"status": "duplicate", "idempotencyKey": key}

    # Recover after a crash between the immutable blob write and the metadata upsert.
    existing = blobs.read_output(request.blobName, idempotency_key=key)
    if existing is not None:
        results.upsert(_output_metadata(existing))
        return {"status": "ok", "idempotencyKey": key, "rows": existing["rows"]}

    started = datetime.now(timezone.utc)
    try:
        data = blobs.download(request.blobName, etag=request.etag)
        # Parse first to preserve the actionable CSV error; validate declared size for otherwise valid inputs.
        rows = parse_csv(data, settings=settings, blob_name=request.blobName)
        if len(data) != request.size:
            raise CsvContractError("Downloaded size differs from queue message")
        response = api.predict_batch(
            rows, blob_name=request.blobName, etag=request.etag
        )
        validate_batch_response(response, rows)
    except StaleBlobVersionError:
        return {"status": "superseded", "idempotencyKey": key}
    except (PermanentInferenceError, CsvContractError) as exc:
        blobs.upload_rejected(
            request.blobName, rejection_reason(request.blobName, str(exc))
        )
        LOGGER.warning("Permanent inference rejection", extra={"status_code": getattr(exc, "status_code", None)})
        return {"status": "rejected", "reason": str(exc)}
    except (MessageError, TransientInferenceError, InferenceError) as exc:
        # Let the Functions host retry; after 5 deliveries the message is moved
        # to inference-requests-poison (host.json maxDequeueCount = 5).
        raise RetryableWorkerError(str(exc)) from exc

    duration_ms = int(
        (datetime.now(timezone.utc) - started).total_seconds() * 1000
    )
    summary = response["summary"]
    metadata = {
        "id": key,
        "idempotencyKey": key,
        "fileName": request.blobName,
        "blobName": request.blobName,
        "etag": request.etag,
        "timestamp": _utc_now(),
        "rows": summary["rows"],
        "atRisk": summary["atRisk"],
        "avgChurnProbability": summary["avgChurnProbability"],
        "modelVersion": response["model_version"],
        "durationMs": duration_ms,
        "status": "ok",
    }
    payload = {
        **metadata,
        "latencyMs": response.get("latency_ms"),
        "summary": summary,
        "predictions": response["predictions"],
    }
    written = blobs.upload_output(request.blobName, payload, idempotency_key=key)
    if not written:
        LOGGER.info("Output already written", extra={"idempotencyKey": key})
        winner = blobs.read_output(request.blobName, idempotency_key=key)
        if winner is None:
            raise RetryableWorkerError("Concurrent output not readable")
        metadata = _output_metadata(winner)
    results.upsert(metadata)
    LOGGER.info(
        "Inference stored",
        extra={
            "blobName": request.blobName,
            "rows": metadata["rows"],
            "atRisk": metadata["atRisk"],
            "durationMs": metadata["durationMs"],
            "status": "ok",
        },
    )
    return {"status": "ok", "idempotencyKey": key, "rows": metadata["rows"]}


def _output_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    fields = ("id", "idempotencyKey", "fileName", "blobName", "etag", "timestamp",
              "rows", "atRisk", "avgChurnProbability", "modelVersion", "durationMs", "status")
    return {field: payload[field] for field in fields}


def recent(
    *, results: ResultStore, settings: Settings, request_origin: str | None
) -> tuple[dict[str, Any], str | None]:
    """Return the payload and the CORS origin to expose (or None)."""
    items = results.recent(settings.recent_limit)
    payload = {
        "count": len(items),
        "limit": settings.recent_limit,
        "results": items,
    }
    allowed = (
        request_origin.rstrip("/")
        if request_origin and settings.dashboard_origin
        and request_origin.rstrip("/") == settings.dashboard_origin
        else None
    )
    return payload, allowed
