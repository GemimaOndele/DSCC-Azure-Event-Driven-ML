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
        {"customerID": ["7590-VHVEG", "5575-GNVDE", "3668-QPYBK"][i], "prediction": "Yes", "label": 1,
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
    assert blobs.containers["output"][f"batch_01.csv.{outcome['idempotencyKey']}.json"][1]["idempotencykey"] == outcome["idempotencyKey"]
    payload = json.loads(blobs.containers["output"][f"batch_01.csv.{outcome['idempotencyKey']}.json"][0])
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


def test_worker_rejects_invalid_csv_without_calling_api() -> None:
    blobs = InMemoryBlobStore({"batch_01.csv": b"invalid,header\n1,2\n"})
    results = InMemoryResultStore()
    class NeverApi:
        def predict_batch(self, *args, **kwargs):
            pytest.fail("Invalid CSV must not reach inference")
    outcome = process(message(), settings=SETTINGS, blobs=blobs, api=NeverApi(), results=results)
    assert outcome["status"] == "rejected"
    assert len(blobs.containers["rejected"]) == 1
    assert not results.items
    assert not blobs.containers["output"]


def test_dispatch_accepts_event_grid_content_length() -> None:
    event = {k: v for k, v in EVENT.items() if k != "size"}
    event["contentLength"] = FIXTURE.stat().st_size
    queue = FakeQueue()
    assert dispatch(event, settings=SETTINGS, blobs=blob_store(), queue=queue)["status"] == "queued"
    assert len(queue.messages) == 1


def test_stale_event_never_scores_new_blob():
    blobs = blob_store()
    blobs.etags["batch_01.csv"] = "new-version"
    queue = FakeQueue()
    assert dispatch(EVENT, settings=SETTINGS, blobs=blobs, queue=queue)["status"] == "superseded"
    assert not queue.messages
    class NeverApi:
        def predict_batch(self, *args, **kwargs):
            pytest.fail("A stale version must not be scored")
    assert process(message(), settings=SETTINGS, blobs=blobs,
                   api=NeverApi(), results=InMemoryResultStore())["status"] == "superseded"


def test_recover_output_after_metadata_failure():
    blobs = blob_store()
    results = InMemoryResultStore()
    outcome = process(message(), settings=SETTINGS, blobs=blobs, api=api(), results=results)
    original = results.items.pop(outcome["idempotencyKey"])
    class NeverApi:
        def predict_batch(self, *args, **kwargs):
            pytest.fail("Recovery must reuse persisted output")
    assert process(message(), settings=SETTINGS, blobs=blobs, api=NeverApi(), results=results)["status"] == "ok"
    assert results.items[outcome["idempotencyKey"]] == original
    assert len(blobs.containers["output"]) == 1


def test_new_version_preserves_old_output():
    blobs, results = blob_store(), InMemoryResultStore()
    first = process(message(), settings=SETTINGS, blobs=blobs, api=api(), results=results)
    blobs.etags["batch_01.csv"] = "new-version"
    new = json.loads(message())
    new["etag"] = "new-version"
    second = process(json.dumps(new), settings=SETTINGS, blobs=blobs, api=api(), results=results)
    assert first["idempotencyKey"] != second["idempotencyKey"]
    assert len(blobs.containers["output"]) == len(results.items) == 2


def test_concurrent_deliveries_share_one_canonical_output():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    blobs, results = blob_store(), InMemoryResultStore()
    barrier = Barrier(2)
    class ConcurrentApi:
        def predict_batch(self, *args, **kwargs):
            barrier.wait(timeout=5)
            return BATCH_RESPONSE
    def run(_):
        return process(message(), settings=SETTINGS, blobs=blobs, api=ConcurrentApi(), results=results)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    assert outcomes[0]["idempotencyKey"] == outcomes[1]["idempotencyKey"]
    assert len(blobs.containers["output"]) == len(results.items) == 1
    persisted = next(iter(results.items.values()))
    blob = json.loads(next(iter(blobs.containers["output"].values()))[0])
    assert persisted["timestamp"] == blob["timestamp"]
    assert persisted["durationMs"] == blob["durationMs"]


def test_invalid_queue_message_is_rejected_without_scoring():
    blobs = blob_store()
    class NeverApi:
        def predict_batch(self, *args, **kwargs):
            pytest.fail("Malformed queue message reached inference")
    assert process('{"invalid": "private-value"}', settings=SETTINGS, blobs=blobs,
                   api=NeverApi(), results=InMemoryResultStore())["status"] == "rejected"
    raw = next(iter(blobs.containers["rejected"].values()))[0]
    assert b"private-value" not in raw


def test_rejection_does_not_expose_raw_cell_values():
    data = FIXTURE.read_bytes().replace(b",Female,", b",PRIVATE-CELL,", 1)
    blobs = InMemoryBlobStore({"batch_01.csv": data})
    outcome = dispatch({**EVENT, "size": len(data)}, settings=SETTINGS, blobs=blobs, queue=FakeQueue())
    assert outcome["status"] == "rejected"
    assert "PRIVATE-CELL" not in outcome["reason"]
    assert b"PRIVATE-CELL" not in next(iter(blobs.containers["rejected"].values()))[0]


@pytest.mark.parametrize("bad_id", ["7590 VHVEG", "a/b"])
def test_dispatch_rejects_bad_id_before_queue(bad_id):
    data = FIXTURE.read_bytes().replace(b"7590-VHVEG", bad_id.encode(), 1)
    blobs, queue = InMemoryBlobStore({"batch_01.csv": data}), FakeQueue()
    outcome = dispatch({**EVENT, "size": len(data)}, settings=SETTINGS, blobs=blobs, queue=queue)
    assert outcome["status"] == "rejected" and not queue.messages
    assert "invalid customerID" in outcome["reason"]
    assert bad_id.encode() not in next(iter(blobs.containers["rejected"].values()))[0]
