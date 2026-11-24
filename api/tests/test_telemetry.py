"""Custom metrics exported to Application Insights (issue #10, R4).

An in-memory OpenTelemetry reader replaces Azure Monitor: the module-level
instruments of api.main are proxies that bind to this provider, so the test
checks exactly what would be exported to the `customMetrics` table.
"""

from fastapi.testclient import TestClient
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

READER = InMemoryMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[READER]))

from api.main import app  # noqa: E402  (provider must exist first)
from api.tests.test_main import CUSTOMER, SECOND_CUSTOMER, THIRD_CUSTOMER  # noqa: E402


def _snapshot() -> dict:
    """{(metric, endpoint, reason): sum or histogram count} — cumulative values."""
    values: dict = {}
    data = READER.get_metrics_data()
    if data is None:
        return values
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            if scope_metrics.scope.name != "dscc.ml_api":
                continue
            for metric in scope_metrics.metrics:
                for point in metric.data.data_points:
                    key = (
                        metric.name,
                        point.attributes.get("endpoint"),
                        point.attributes.get("reason"),
                    )
                    value = getattr(point, "value", None)
                    values[key] = point.count if value is None else value
    return values


def _delta(before: dict, after: dict, name: str, endpoint: str, reason=None) -> float:
    key = (name, endpoint, reason)
    return after.get(key, 0) - before.get(key, 0)


def test_custom_metrics_count_rows_calls_and_latency() -> None:
    with TestClient(app) as client:
        before = _snapshot()
        assert client.post("/predict", json=CUSTOMER).status_code == 200
        response = client.post(
            "/predict/batch",
            json={"rows": [CUSTOMER, SECOND_CUSTOMER, THIRD_CUSTOMER]},
            headers={"X-DSCC-Blob": "batch_01.csv"},
        )
        assert response.status_code == 200
        after = _snapshot()

    assert _delta(before, after, "inferred_rows", "/predict") == 1
    assert _delta(before, after, "inferred_rows", "/predict/batch") == 3
    assert _delta(before, after, "inference_requests", "/predict") == 1
    assert _delta(before, after, "inference_requests", "/predict/batch") == 1
    # Histogram: one latency sample per successful call.
    assert _delta(before, after, "inference_latency_ms", "/predict") == 1
    assert _delta(before, after, "inference_latency_ms", "/predict/batch") == 1


def test_custom_metrics_count_rejections_by_reason() -> None:
    with TestClient(app) as client:
        before = _snapshot()
        invalid = {**CUSTOMER, "gender": "Unknown"}
        assert client.post("/predict", json=invalid).status_code == 422
        assert client.post("/predict/batch", json={"rows": []}).status_code == 422
        non_finite = b'{"rows": [{"MonthlyCharges": NaN}]}'
        assert (
            client.post(
                "/predict/batch",
                content=non_finite,
                headers={"content-type": "application/json"},
            ).status_code
            == 422
        )
        # Non-prediction routes are not counted as inference errors.
        assert client.get("/does-not-exist").status_code == 404
        after = _snapshot()

    assert _delta(before, after, "inference_errors", "/predict", "validation") == 1
    assert _delta(before, after, "inference_errors", "/predict/batch", "validation") == 2
    assert _delta(before, after, "inferred_rows", "/predict") == 0
    assert _delta(before, after, "inferred_rows", "/predict/batch") == 0
