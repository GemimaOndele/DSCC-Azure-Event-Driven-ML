from fastapi.testclient import TestClient

from api.main import app


CUSTOMER = {
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
