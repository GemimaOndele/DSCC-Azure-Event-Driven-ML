import httpx
import pytest

from src.api_client import (
    InferenceClient,
    PermanentInferenceError,
    TransientInferenceError,
)

ROWS = [{"customerID": "7590-VHVEG", "gender": "Female"}]
BATCH_RESPONSE = {
    "model_version": "1.0.0",
    "latency_ms": 12.3,
    "predictions": [
        {
            "customerID": "7590-VHVEG",
            "prediction": "No",
            "label": 0,
            "churn_probability": 0.12,
            "confidence": 0.88,
        }
    ],
    "summary": {
        "rows": 1,
        "atRisk": 0,
        "avgChurnProbability": 0.12,
        "threshold": 0.5,
        "model_version": "1.0.0",
    },
}


def client_for(handler) -> InferenceClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return InferenceClient("http://api:8000", client=http)


def test_success_posts_rows_to_the_batch_route() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = __import__("json").loads(request.content)
        seen["blob"] = request.headers.get("X-DSCC-Blob")
        return httpx.Response(200, json=BATCH_RESPONSE)

    client = client_for(handler)
    result = client.predict_batch(ROWS, blob_name="batch.csv", etag="e1")
    assert result == BATCH_RESPONSE
    assert seen["url"] == "http://api:8000/predict/batch"
    assert seen["body"] == {"rows": ROWS}
    assert seen["blob"] == "batch.csv"


@pytest.mark.parametrize("status", [400, 404, 422])
def test_permanent_statuses(status: int) -> None:
    client = client_for(lambda request: httpx.Response(status, text="bad row 2"))
    with pytest.raises(PermanentInferenceError) as exc:
        client.predict_batch(ROWS, blob_name="batch.csv", etag="e1")
    assert exc.value.status_code == status
    assert "bad row 2" in str(exc.value)


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_statuses(status: int) -> None:
    client = client_for(lambda request: httpx.Response(status, text="try later"))
    with pytest.raises(TransientInferenceError) as exc:
        client.predict_batch(ROWS, blob_name="batch.csv", etag="e1")
    assert exc.value.status_code == status


def test_timeout_is_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow API", request=request)

    with pytest.raises(TransientInferenceError, match="timeout"):
        client_for(handler).predict_batch(ROWS, blob_name="batch.csv", etag="e1")


def test_invalid_success_payload_is_transient() -> None:
    client = client_for(lambda request: httpx.Response(200, text="not json"))
    with pytest.raises(TransientInferenceError, match="invalid JSON"):
        client.predict_batch(ROWS, blob_name="batch.csv", etag="e1")
