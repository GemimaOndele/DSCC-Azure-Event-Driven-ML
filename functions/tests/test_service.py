import json
from pathlib import Path

import httpx
import pytest

from src.api_client import InferenceClient, PermanentInferenceError, TransientInferenceError
from src.config import Settings
from src.service import RetryableWorkerError, dispatch, process, recent
from tests.fakes import FakeQueue, InMemoryBlobStore, InMemoryResultStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "valid_batch.csv"
SETTINGS = Settings(dashboard_origin="https://dashboard.example")
EVENT = {
    "url": "https://account.blob.core.windows.net/input/batch_01.csv",
    "etag": "0x8DC-A1",
    "size": FIXTURE.stat().st_size,
    "blobName": "batch_01.csv",
}
BATCH_RESPONSE = {
    "model_version": "1.0.0",
    "latency_ms": 12.3,
    "predictions": [
        {"customerID": f"c{i}", "prediction": "Yes", "label": 1,
         "churn_probability": 0.8, "confidence": 0.8}
        for i in range(3)
    ],
    "summary": {
        "rows": 3,
        "atRisk": 3,
        "avgChurnProbability": 0.8,
        "threshold": 0.5,
        "model_version": "1.0.0",
    },
}


def blob_store() -> InMemoryBlobStore:
    return InMemoryBlobStore({"batch_01.csv": FIXTURE.read_bytes()})


def api(status: int = 200) -> InferenceClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if status == 200:
            return httpx.Response(200, json=BATCH_RESPONSE)
        return httpx.Response(status, text="error")

    return InferenceClient(
        "http://api:8000",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def message() -> str:
    return json.dumps(
        {
            "blobName": "batch_01.csv",
            "etag": "0x8DC-A1",
            "size": FIXTURE.stat().st_size,
            "enqueuedAt": "2026-11-24T10:00:00Z",
        }
    )


def test_dispatch_enqueues_a_valid_csv() -> None:
    blobs, queue = blob_store(), FakeQueue()
    result = dispatch(EVENT, settings=SETTINGS, blobs=blobs, queue=queue)
    assert result == {"status": "queued", "blobName": "batch_01.csv", "rows": 3}
    assert len(queue.messages) == 1
    assert json.loads(queue.messages[0])["blobName"] == "batch_01.csv"
    assert blobs.writes == []


def test_dispatch_rejects_bad_extension_and_bad_columns() -> None:
    blobs, queue = blob_store(), FakeQueue()
    result = dispatch({**EVENT, "blobName": "batch.txt"}, settings=SETTINGS,
                      blobs=blobs, queue=queue)
    assert result["status"] == "rejected"
    assert ".csv" in result["reason"]
    assert len(blobs.containers["rejected"]) == 1
    assert queue.messages == []

    broken = FIXTURE.read_bytes().replace(b"customerID,", b"id,")
    blobs = InMemoryBlobStore({"batch_01.csv": broken})
    result = dispatch({**EVENT, "size": len(broken)}, settings=SETTINGS,
                      blobs=blobs, queue=queue)
    assert result["status"] == "rejected"
    assert "missing columns" in result["reason"]


def test_worker_writes_output_and_metadata() -> None:
    blobs, results = blob_store(), InMemoryResultStore()
    outcome = process(message(), settings=SETTINGS, blobs=blobs, api=api(), results=results)
    assert outcome["status"] == "ok"
    assert outcome["rows"] == 3
    assert blobs.containers["output"]["batch_01.csv.json"][1]["idempotencykey"] == outcome["idempotencyKey"]
    payload = json.loads(blobs.containers["output"]["batch_01.csv.json"][0])
    assert len(payload["predictions"]) == 3
    assert payload["summary"]["atRisk"] == 3

    metadata = results.items[outcome["idempotencyKey"]]
    assert metadata["fileName"] == "batch_01.csv"
    assert metadata["etag"] == "0x8DC-A1"
    assert metadata["rows"] == 3
    assert metadata["atRisk"] == 3
    assert metadata["avgChurnProbability"] == 0.8
    assert metadata["modelVersion"] == "1.0.0"
    assert metadata["status"] == "ok"
    assert metadata["durationMs"] >= 0


def test_worker_does_not_retry_permanent_errors() -> None:
    blobs, results = blob_store(), InMemoryResultStore()
    outcome = process(message(), settings=SETTINGS, blobs=blobs, api=api(422), results=results)
    assert outcome["status"] == "rejected"
    assert len(blobs.containers["rejected"]) == 1
    assert blobs.containers["output"] == {}
    assert results.items == {}


def test_worker_raises_on_transient_errors_for_the_host() -> None:
    with pytest.raises(RetryableWorkerError):
        process(message(), settings=SETTINGS, blobs=blob_store(), api=api(503),
                results=InMemoryResultStore())


def test_duplicate_delivery_is_idempotent() -> None:
    blobs, results = blob_store(), InMemoryResultStore()

    class CountingApi:
        calls = 0

        def predict_batch(self, rows, *, blob_name, etag):
            self.calls += 1
            return BATCH_RESPONSE

    counter = CountingApi()
    first = process(message(), settings=SETTINGS, blobs=blobs, api=counter, results=results)
    second = process(message(), settings=SETTINGS, blobs=blobs, api=counter, results=results)
    assert first["status"] == "ok"
    assert second["status"] == "duplicate"
    assert counter.calls == 1
    assert len(blobs.containers["output"]) == 1


def test_recent_limits_and_cors_origin() -> None:
    results = InMemoryResultStore()
    for i in range(25):
        results.upsert({"idempotencyKey": f"k{i}", "id": f"k{i}",
                        "fileName": f"b{i}.csv", "timestamp": f"2026-11-24T10:{i:02d}:00Z",
                        "rows": 3, "status": "ok", "atRisk": 1,
                        "avgChurnProbability": 0.4, "modelVersion": "1.0.0",
                        "durationMs": 12})
    payload, origin = recent(results=results, settings=SETTINGS,
                             request_origin="https://dashboard.example")
    assert payload["count"] == 20
    assert payload["limit"] == 20
    assert origin == "https://dashboard.example"

    _, denied = recent(results=results, settings=SETTINGS,
                       request_origin="https://evil.example")
    assert denied is None
    _, anonymous = recent(results=results, settings=SETTINGS, request_origin=None)
    assert anonymous is None
