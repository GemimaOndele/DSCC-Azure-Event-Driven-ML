"""Exercise production storage adapters against an isolated loopback Azurite.

No real Azure credentials, cloud endpoints or dataset download. The factories
are injected only in tests; the production adapters still use managed identity.
"""
import base64
import csv
import io
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "functions"))

from api.main import app
from src.api_client import InferenceClient
from src.azure_clients import AzureBlobStore, AzureQueueSender, TableResultStore
from src.config import Settings
from src.contract import load_feature_contract, required_columns
from src.ports import StaleBlobVersionError
from src.service import dispatch, process, recent

pytestmark = pytest.mark.skipif(
    os.environ.get("DSCC_RUN_AZURITE") != "1",
    reason="Requires the isolated local Azurite emulator",
)
ACCOUNT = "dsccemulator"
# Deliberately public, emulator-only key; never usable with an Azure account.
KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


def synthetic_csv(count=3):
    specs = load_feature_contract()["features"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=required_columns(), lineterminator="\n")
    writer.writeheader()
    for i in range(count):
        row = {"customerID": f"synthetic-{i+1}"}
        for spec in specs:
            row[spec["name"]] = (
                spec["allowed_values"][i % len(spec["allowed_values"])]
                if spec["kind"] == "categorical"
                else spec["allowed_range"][0]
            )
        writer.writerow(row)
    return buffer.getvalue().encode()


@pytest.fixture
def storage(monkeypatch):
    import azure.identity
    import azure.storage.blob
    import azure.storage.queue
    import azure.data.tables
    from azure.storage.blob import BlobServiceClient
    from azure.storage.queue import QueueServiceClient
    from azure.data.tables import TableServiceClient

    blob_sdk = BlobServiceClient(
        account_url=f"http://127.0.0.1:10000/{ACCOUNT}",
        credential=KEY,
        api_version="2023-11-03",
        retry_total=0,
    )
    queue_sdk = QueueServiceClient(
        account_url=f"http://127.0.0.1:10001/{ACCOUNT}",
        credential=KEY,
        api_version="2023-11-03",
        retry_total=0,
    )
    table_sdk = TableServiceClient(
        endpoint=f"http://127.0.0.1:10002/{ACCOUNT}",
        credential=KEY,
        retry_total=0,
    )
    suffix = uuid.uuid4().hex[:10]
    containers = {kind: f"{kind}-{suffix}" for kind in ("input", "output", "rejected")}
    for name in containers.values():
        blob_sdk.create_container(name)
    queue_name, table_name = f"requests-{suffix}", f"inferences{suffix}"
    raw_queue = queue_sdk.create_queue(queue_name)
    table = table_sdk.create_table(table_name)
    # The classes under test import the SDK factories in their constructors.
    # Return genuine SDK clients, but confined to the loopback emulator.
    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(azure.storage.blob, "BlobServiceClient", lambda **kw: blob_sdk)
    monkeypatch.setattr(azure.storage.queue, "QueueServiceClient", lambda **kw: queue_sdk)
    monkeypatch.setattr(azure.data.tables, "TableServiceClient", lambda **kw: table_sdk)
    blobs = AzureBlobStore(ACCOUNT, containers)
    queue = AzureQueueSender(ACCOUNT, queue_name)
    results = TableResultStore(ACCOUNT, table_name)
    yield blobs, queue, results, blob_sdk, raw_queue, table, containers
    # The CI runner destroys the entire disposable emulator, not cloud resources.


def put(blob_sdk, containers, name, data):
    client = blob_sdk.get_blob_client(containers["input"], name)
    response = client.upload_blob(data, overwrite=True)
    return {"blobName": name, "eTag": response["etag"], "contentLength": len(data)}


def test_sdk_pipeline_queue_encoding_and_metadata_recovery(storage):
    blobs, queue, results, blob_sdk, raw_queue, table, containers = storage
    name = "synthetic-batch.csv"
    event = put(blob_sdk, containers, name, synthetic_csv())
    settings = Settings(dashboard_origin="https://dashboard.example")
    assert dispatch(event, settings=settings, blobs=blobs, queue=queue)["status"] == "queued"

    # Inspect the actual message body stored by Azure Queue SDK. The Functions
    # host's default queue encoding is Base64; decode that exact payload.
    messages = list(raw_queue.receive_messages(messages_per_page=1, max_messages=1))
    assert len(messages) == 1
    raw = base64.b64decode(messages[0].content, validate=True).decode("utf-8")
    envelope = json.loads(raw)
    assert envelope["blobName"] == name
    assert envelope["etag"] == event["eTag"]

    with TestClient(app) as http:
        api = InferenceClient("http://testserver", client=http)
        outcome = process(raw, settings=settings, blobs=blobs, api=api, results=results)
        assert outcome["status"] == "ok" and outcome["rows"] == 3
        key = outcome["idempotencyKey"]
        assert process(raw, settings=settings, blobs=blobs, api=api, results=results)["status"] == "duplicate"
        persisted = blobs.read_output(name, idempotency_key=key)
        assert persisted["rows"] == 3 and len(persisted["predictions"]) == 3
        assert all(0 <= p["churn_probability"] <= 1 for p in persisted["predictions"])
        assert len(list(blob_sdk.get_container_client(containers["output"]).list_blobs())) == 1
        # Simulate the output having been persisted but metadata not committed.
        table.delete_entity(partition_key="inference", row_key=key)

        class NeverCallAPI:
            def predict_batch(self, *args, **kwargs):
                pytest.fail("Recovery must use the existing canonical output")

        assert process(raw, settings=settings, blobs=blobs, api=NeverCallAPI(), results=results)["status"] == "ok"
    raw_queue.delete_message(messages[0])
    payload, origin = recent(results=results, settings=settings, request_origin="https://dashboard.example")
    assert origin == "https://dashboard.example"
    assert payload["count"] == 1
    item = payload["results"][0]
    assert item["rows"] == 3 and type(item["rows"]) is int
    assert type(item["avgChurnProbability"]) is float
    assert item["id"] == key and item["timestamp"] == persisted["timestamp"]


def test_sdk_etag_prevents_scoring_replaced_blob(storage):
    blobs, queue, _, blob_sdk, raw_queue, _, containers = storage
    name = "replaced.csv"
    original = put(blob_sdk, containers, name, synthetic_csv(1))
    replacement = put(blob_sdk, containers, name, synthetic_csv(2))
    assert original["eTag"] != replacement["eTag"]
    with pytest.raises(StaleBlobVersionError):
        blobs.download(name, etag=original["eTag"])
    assert dispatch(original, settings=Settings(), blobs=blobs, queue=queue)["status"] == "superseded"
    assert not list(raw_queue.peek_messages())
    assert dispatch(replacement, settings=Settings(), blobs=blobs, queue=queue)["status"] == "queued"


def test_sdk_create_only_concurrent_results_and_private_rejection(storage):
    blobs, queue, _, blob_sdk, raw_queue, _, containers = storage
    name = "atomic.csv"
    key = "atomic-1234567890abcdef"

    def write(value):
        return blobs.upload_output(name, {"value": value}, idempotency_key=key)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, [1, 2]))
    assert sorted(outcomes) == [False, True]
    assert blobs.read_output(name, idempotency_key=key)["value"] == (1 if outcomes[0] else 2)

    event = put(blob_sdk, containers, "invalid.csv", synthetic_csv(1).replace(b"synthetic-1", b"private/id"))
    assert dispatch(event, settings=Settings(), blobs=blobs, queue=queue)["status"] == "rejected"
    assert not list(raw_queue.peek_messages())
    reason = blob_sdk.get_blob_client(containers["rejected"], "invalid.csv.reason.json").download_blob().readall()
    assert b"private/id" not in reason
    assert "invalid customerID" in json.loads(reason)["reason"]
