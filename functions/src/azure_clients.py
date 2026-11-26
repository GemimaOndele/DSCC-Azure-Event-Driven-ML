"""Azure SDK adapters. Managed identity only: no key or connection string."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from .api_client import InferenceClient
from .config import Settings
from .ports import BlobStore, QueueSender, ResultStore, StaleBlobVersionError

LOGGER = logging.getLogger("dscc.pipeline.azure")


class AzureBlobStore:
    def __init__(self, account_name: str, containers: dict[str, str]) -> None:
        from azure.core.exceptions import ResourceExistsError
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        self._service = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        self._names = containers
        for container in containers.values():
            try:
                self._service.create_container(container)
            except ResourceExistsError:
                pass

    def download(self, name: str, *, etag: str) -> bytes:
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError, HttpResponseError

        quoted = etag if etag.startswith('"') else f'"{etag}"'
        try:
            return self._service.get_blob_client(self._names["input"], name).download_blob(
                etag=quoted, match_condition=MatchConditions.IfNotModified
            ).readall()
        except (ResourceModifiedError, ResourceNotFoundError) as exc:
            raise StaleBlobVersionError("Input version is no longer available") from exc
        except HttpResponseError as exc:
            if exc.status_code == 412:
                raise StaleBlobVersionError("Input version is no longer available") from exc
            raise

    def _output_client(self, name: str, key: str):
        return self._service.get_blob_client(self._names["output"], f"{name}.{key}.json")

    def read_output(self, name: str, *, idempotency_key: str) -> dict[str, Any] | None:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            return json.loads(self._output_client(name, idempotency_key).download_blob().readall())
        except ResourceNotFoundError:
            return None

    def upload_rejected(self, name: str, reason: dict[str, Any]) -> str:
        blob_name = f"{name}.reason.json"
        self._service.get_blob_client(self._names["rejected"], blob_name).upload_blob(
            json.dumps(reason, ensure_ascii=False, indent=2),
            overwrite=True,
            content_type="application/json",
        )
        return blob_name

    def upload_output(
        self, name: str, payload: dict[str, Any], *, idempotency_key: str
    ) -> bool:
        from azure.core.exceptions import ResourceExistsError
        client = self._output_client(name, idempotency_key)
        try:
            client.upload_blob(
                json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
                overwrite=False,
                content_type="application/json",
                metadata={"idempotencykey": idempotency_key},
            )
            return True
        except ResourceExistsError:
            return False


class AzureQueueSender:
    def __init__(self, account_name: str, queue_name: str = "inference-requests") -> None:
        from azure.core.exceptions import ResourceExistsError
        from azure.identity import DefaultAzureCredential
        from azure.storage.queue import QueueServiceClient

        self._service = QueueServiceClient(
            account_url=f"https://{account_name}.queue.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        try:
            self._service.create_queue(queue_name)
        except ResourceExistsError:
            pass
        self._queue = self._service.get_queue_client(queue_name)

    def send_message(self, text: str) -> None:
        self._queue.send_message(text)


class CosmosResultStore:
    def __init__(self, endpoint: str, database: str = "pipeline", container: str = "inferences") -> None:
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential

        client = CosmosClient(endpoint, credential=DefaultAzureCredential())
        self._container = client.get_database_client(database).get_container_client(container)

    def upsert(self, metadata: dict[str, Any]) -> None:
        self._container.upsert_item(metadata)

    def exists(self, idempotency_key: str, *, file_name: str) -> bool:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            self._container.read_item(idempotency_key, partition_key=file_name)
        except CosmosResourceNotFoundError:
            return False
        return True

    def recent(self, limit: int) -> list[dict[str, Any]]:
        items = list(
            self._container.query_items(
                query=(
                    "SELECT TOP @limit * FROM c WHERE c.status = 'ok' "
                    "ORDER BY c.timestamp DESC"
                ),
                parameters=[{"name": "@limit", "value": limit}],
                enable_cross_partition_query=True,
            )
        )
        return _project(items)


class TableResultStore:
    """Fallback when Cosmos free tier is unavailable (issue #7)."""

    def __init__(self, account_name: str, table: str = "inferences") -> None:
        from azure.data.tables import TableServiceClient
        from azure.identity import DefaultAzureCredential

        service = TableServiceClient(
            endpoint=f"https://{account_name}.table.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        self._table = service.create_table_if_not_exists(table)

    def upsert(self, metadata: dict[str, Any]) -> None:
        entity = {
            "PartitionKey": "inference",
            "RowKey": metadata["idempotencyKey"],
            **metadata,
        }
        self._table.upsert_entity(entity)

    def exists(self, idempotency_key: str, *, file_name: str) -> bool:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            self._table.get_entity("inference", idempotency_key)
        except ResourceNotFoundError:
            return False
        return True

    def recent(self, limit: int) -> list[dict[str, Any]]:
        entities = self._table.query_entities("PartitionKey eq 'inference'", results_per_page=limit)
        items = sorted(entities, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        return _project(
            [
                {key: value for key, value in item.items() if not key.startswith("odata")}
                for item in items
            ]
        )


def _project(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "id",
        "fileName",
        "timestamp",
        "rows",
        "atRisk",
        "avgChurnProbability",
        "modelVersion",
        "durationMs",
        "status",
    )
    return [
        {field: item.get(field) for field in fields if field in item}
        for item in items
    ]


@lru_cache(maxsize=1)
def get_clients() -> tuple[Settings, BlobStore, QueueSender, InferenceClient, ResultStore]:
    """One set of clients per worker process (HTTP connections are reused)."""
    settings = Settings.from_env()
    if not settings.storage_account:
        raise RuntimeError("STORAGE_ACCOUNT must be set")
    blobs: BlobStore = AzureBlobStore(
        settings.storage_account,
        {"input": "input", "output": "output", "rejected": "rejected"},
    )
    queue: QueueSender = AzureQueueSender(settings.storage_account)
    api = InferenceClient(
        settings.model_api_url,
        connect_timeout=settings.api_connect_timeout_s,
        read_timeout=settings.api_read_timeout_s,
    )
    if settings.cosmos_endpoint:
        results: ResultStore = CosmosResultStore(settings.cosmos_endpoint)
    else:
        LOGGER.warning("COSMOS_ENDPOINT is empty: falling back to Table Storage")
        results = TableResultStore(settings.storage_account)
    return settings, blobs, queue, api, results
