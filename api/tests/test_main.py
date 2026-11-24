import json

from fastapi.testclient import TestClient

from api.main import DECISION_THRESHOLD, MAX_BATCH_ROWS, app


CUSTOMER = {
    "customerID": "7590-VHVEG",
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 12,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 55.0,
    "TotalCharges": 660.0,
    "numAdminTickets": 0,
    "numTechTickets": 1,
}

SECOND_CUSTOMER = {
    **CUSTOMER,
    "customerID": "5575-GNVDE",
    "gender": "Male",
    "Partner": "No",
    "tenure": 1,
    "InternetService": "Fiber optic",
    "Contract": "One year",
    "PaymentMethod": "Mailed check",
    "MonthlyCharges": 75.5,
    # TotalCharges omitted on purpose: the training pipeline imputes it.
    "TotalCharges": None,
}

THIRD_CUSTOMER = {
    **CUSTOMER,
    "customerID": "4804-JKQVI",
    "gender": "Male",
    "tenure": 48,
    "InternetService": "No",
    "OnlineSecurity": "No internet service",
    "OnlineBackup": "No internet service",
    "DeviceProtection": "No internet service",
    "TechSupport": "No internet service",
    "StreamingTV": "No internet service",
    "StreamingMovies": "No internet service",
    "Contract": "Two year",
    "MonthlyCharges": 20.05,
    "TotalCharges": 962.4,
    "numTechTickets": 0,
}


def test_prediction_and_api_routes() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        version = client.get("/version")
        response = client.post("/predict", json=CUSTOMER)
        metrics = client.get("/metrics")

    assert health.status_code == 200
    assert health.json()["model_loaded"] is True
    assert health.json()["model_load_time_ms"] >= 0
    assert version.json() == {"api_version": "1.0.0", "model_version": "1.0.0"}
    assert response.status_code == 200
    assert response.json()["prediction"] in {"No", "Yes"}
    assert 0.0 <= response.json()["churn_probability"] <= 1.0
    assert 0.0 <= response.json()["confidence"] <= 1.0
    assert response.json()["model_version"] == "1.0.0"
    assert metrics.json()["inference_calls"] == 1
    assert metrics.json()["average_latency_ms"] >= 0


def test_invalid_input_returns_422() -> None:
    invalid_customer = {**CUSTOMER, "tenure": "not-a-number"}

    with TestClient(app) as client:
        response = client.post("/predict", json=invalid_customer)

    assert response.status_code == 422


def test_missing_body_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post("/predict")

    assert response.status_code == 422


def test_batch_predict_multi_client_csv_rows() -> None:
    """Contract #14 option A: one POST for all rows of a multi-client CSV."""
    rows = [CUSTOMER, SECOND_CUSTOMER, THIRD_CUSTOMER]

    with TestClient(app) as client:
        response = client.post("/predict/batch", json={"rows": rows})
        metrics = client.get("/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "1.0.0"
    assert body["latency_ms"] >= 0
    assert len(body["predictions"]) == 3
    assert [p["customerID"] for p in body["predictions"]] == [
        "7590-VHVEG",
        "5575-GNVDE",
        "4804-JKQVI",
    ]
    for prediction in body["predictions"]:
        assert 0.0 <= prediction["churn_probability"] <= 1.0
        assert prediction["label"] in {0, 1}
        assert prediction["prediction"] == ("Yes" if prediction["label"] else "No")
        assert 0.0 <= prediction["confidence"] <= 1.0

    summary = body["summary"]
    assert summary["rows"] == 3
    assert summary["atRisk"] == sum(p["label"] for p in body["predictions"])
    assert summary["threshold"] == DECISION_THRESHOLD
    assert summary["model_version"] == "1.0.0"
    assert abs(
        summary["avgChurnProbability"]
        - sum(p["churn_probability"] for p in body["predictions"]) / 3
    ) < 1e-6
    # One HTTP request counts as one inference call, whatever the row count.
    assert metrics.json()["inference_calls"] == 1


def test_batch_empty_rows_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post("/predict/batch", json={"rows": []})

    assert response.status_code == 422


def test_batch_extra_or_missing_field_returns_422() -> None:
    with TestClient(app) as client:
        extra = client.post(
            "/predict/batch", json={"rows": [{**CUSTOMER, "unexpected": 1}]}
        )
        incomplete = client.post(
            "/predict/batch",
            json={"rows": [{k: v for k, v in CUSTOMER.items() if k != "numTechTickets"}]},
        )

    assert extra.status_code == 422
    assert incomplete.status_code == 422


def test_batch_unknown_category_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict/batch", json={"rows": [{**CUSTOMER, "gender": "Unknown"}]}
        )

    assert response.status_code == 422


def test_batch_non_finite_number_returns_422() -> None:
    payload = json.dumps({"rows": [{**CUSTOMER, "MonthlyCharges": float("nan")}]})
    with TestClient(app) as client:
        response = client.post(
            "/predict/batch", content=payload, headers={"content-type": "application/json"}
        )

    assert response.status_code == 422


def test_batch_row_cap_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict/batch", json={"rows": [CUSTOMER] * (MAX_BATCH_ROWS + 1)}
        )

    assert response.status_code == 422
