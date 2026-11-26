"""Offline integration of the real ONNX API and pipeline orchestration.

Run after #17/#18/#21 and this branch are integrated. No cloud, no dataset download.
"""
import csv
import io
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

from api.main import app
from src.api_client import InferenceClient
from src.config import Settings
from src.contract import load_feature_contract, required_columns
from src.service import RetryableWorkerError, dispatch, process, recent
from tests.fakes import FakeQueue, InMemoryBlobStore, InMemoryResultStore


def synthetic_csv(count=3):
    specs = load_feature_contract()["features"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=required_columns(), lineterminator="\n")
    writer.writeheader()
    for i in range(count):
        row = {"customerID": f"synthetic-{i+1}"}
        for spec in specs:
            if spec["kind"] == "categorical":
                row[spec["name"]] = spec["allowed_values"][i % len(spec["allowed_values"])]
            else:
                row[spec["name"]] = spec["allowed_range"][0]
        writer.writerow(row)
    return buffer.getvalue().encode()


def test_real_onnx_inference_through_dispatch_worker_recent():
    data = synthetic_csv()
    name = "synthetic-batch.csv"
    blobs = InMemoryBlobStore({name: data})
    results, queue = InMemoryResultStore(), FakeQueue()
    settings = Settings(dashboard_origin="https://dashboard.example")
    event = {"blobName": name, "eTag": "0x8DC-A1", "contentLength": len(data)}
    assert dispatch(event, settings=settings, blobs=blobs, queue=queue)["status"] == "queued"
    assert len(queue.messages) == 1
    with TestClient(app) as http:
        assert http.get("/health").status_code == 200
        api = InferenceClient("http://testserver", client=http)
        outcome = process(queue.messages[0], settings=settings, blobs=blobs, api=api, results=results)
        assert outcome["status"] == "ok" and outcome["rows"] == 3
        assert process(queue.messages[0], settings=settings, blobs=blobs, api=api, results=results)["status"] == "duplicate"
    payload = json.loads(next(iter(blobs.containers["output"].values()))[0])
    assert [p["customerID"] for p in payload["predictions"]] == [f"synthetic-{i+1}" for i in range(3)]
    assert all(0 <= p["churn_probability"] <= 1 for p in payload["predictions"])
    assert len(blobs.containers["output"]) == 1
    data, origin = recent(results=results, settings=settings, request_origin="https://dashboard.example")
    assert data["count"] == 1 and data["results"][0]["rows"] == 3
    assert origin == "https://dashboard.example"


def test_invalid_csv_is_rejected_before_enqueue():
    data = b"wrong,header\n1,2\n"
    name = "synthetic-invalid.csv"
    blobs = InMemoryBlobStore({name: data})
    queue = FakeQueue()
    outcome = dispatch({"blobName": name, "eTag": "0x8DC-A1", "contentLength": len(data)},
                       settings=Settings(), blobs=blobs, queue=queue)
    assert outcome["status"] == "rejected"
    assert not queue.messages and len(blobs.containers["rejected"]) == 1
