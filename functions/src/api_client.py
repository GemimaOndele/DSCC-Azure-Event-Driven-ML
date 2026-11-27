"""HTTP client for POST /predict/batch with explicit retry classification."""

from __future__ import annotations

from typing import Any, Protocol

import httpx
import math


PERMANENT_STATUSES = frozenset({400, 401, 403, 404, 405, 409, 422})
TRANSIENT_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


class InferenceError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class PermanentInferenceError(InferenceError):
    """Bad request / schema error: do not retry, write a rejection reason."""


class TransientInferenceError(InferenceError):
    """Server or network error: let the queue host retry (maxDequeueCount=5)."""


class HttpPoster(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...


class InferenceClient:
    """Small wrapper around httpx so tests can inject ``httpx.MockTransport``."""

    def __init__(
        self,
        base_url: str,
        *,
        client: HttpPoster | None = None,
        connect_timeout: float = 2.0,
        read_timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client()
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()  # type: ignore[attr-defined]

    def predict_batch(
        self, rows: list[dict[str, Any]], *, blob_name: str, etag: str
    ) -> dict[str, Any]:
        try:
            response = self._client.post(
                f"{self.base_url}/predict/batch",
                json={"rows": rows},
                timeout=self._timeout,
                headers={
                    "X-DSCC-Blob": blob_name,
                    "X-DSCC-ETag": etag,
                    "User-Agent": "dscc-event-pipeline/1.0",
                },
            )
        except httpx.TimeoutException as exc:
            raise TransientInferenceError("API timeout") from exc
        except httpx.HTTPError as exc:
            raise TransientInferenceError("API connection error") from exc

        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError as exc:
                raise TransientInferenceError("API returned invalid JSON") from exc
            if not isinstance(payload, dict) or not isinstance(
                payload.get("predictions"), list
            ):
                raise TransientInferenceError("API response has no predictions list")
            validate_batch_response(payload, rows)
            return payload

        # Do not persist response bodies: validation errors can echo client data.
        message = f"API returned HTTP {response.status_code}"
        if response.status_code in PERMANENT_STATUSES:
            raise PermanentInferenceError(message, status_code=response.status_code)
        if response.status_code in TRANSIENT_STATUSES:
            raise TransientInferenceError(message, status_code=response.status_code)
        # Unknown status: conservative choice, bounded by maxDequeueCount.
        raise TransientInferenceError(message, status_code=response.status_code)


def validate_batch_response(payload: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """Reject malformed or inconsistent success responses before persistence."""
    def number(value: Any, minimum: float, maximum: float) -> bool:
        try:
            return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum
        except OverflowError:
            return False

    def fail() -> None:
        raise TransientInferenceError("API returned inconsistent batch response")

    if not isinstance(payload, dict):
        fail()
    predictions, summary = payload.get("predictions"), payload.get("summary")
    version = payload.get("model_version")
    if (not isinstance(predictions, list) or not isinstance(summary, dict)
            or not isinstance(version, str) or not version.strip()
            or len(predictions) != len(rows) or not rows
            or not number(payload.get("latency_ms"), 0, float("inf"))):
        fail()
    if (type(summary.get("rows")) is not int or summary["rows"] != len(rows)
            or type(summary.get("atRisk")) is not int
            or summary.get("model_version") != version
            or not number(summary.get("threshold"), 0, 1)
            or not number(summary.get("avgChurnProbability"), 0, 1)):
        fail()
    probabilities = []
    labels = []
    for row, item in zip(rows, predictions):
        if (not isinstance(item, dict) or item.get("customerID") != row.get("customerID")
                or type(item.get("label")) is not int or item["label"] not in (0, 1)
                or item.get("prediction") != ("Yes" if item["label"] else "No")
                or not number(item.get("churn_probability"), 0, 1)
                or not number(item.get("confidence"), 0, 1)):
            fail()
        probabilities.append(item["churn_probability"])
        labels.append(item["label"])
    if (sum(labels) != summary["atRisk"]
            or not math.isclose(sum(probabilities) / len(rows), summary["avgChurnProbability"], abs_tol=1e-5)):
        fail()
