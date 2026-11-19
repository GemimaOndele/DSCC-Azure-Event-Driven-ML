import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import AsyncGenerator, Literal

import numpy as np
import onnxruntime
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict


API_VERSION = os.getenv("API_VERSION", "1.0.0")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")
MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        str(
            Path(__file__).resolve().parents[1]
            / "model"
            / f"model-{MODEL_VERSION}.onnx"
        ),
    )
)
LOGGER = logging.getLogger("dscc.ml_api")


class CustomerFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: str
    SeniorCitizen: int
    Partner: str
    Dependents: str
    tenure: int
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float
    TotalCharges: float | None = None
    numAdminTickets: int
    numTechTickets: int


class PredictionResponse(BaseModel):
    prediction: Literal["No", "Yes"]
    churn_probability: float
    confidence: float
    model_version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        configure_azure_monitor(
            connection_string=connection_string,
            logger_name=LOGGER.name,
        )
        LOGGER.info("Azure Monitor OpenTelemetry configured")
    else:
        LOGGER.warning(
            "Azure Monitor telemetry is disabled: "
            "APPLICATIONINSIGHTS_CONNECTION_STRING is not set"
        )

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model artifact not found: {MODEL_PATH}")

    load_started = perf_counter()
    app.state.model = onnxruntime.InferenceSession(
        str(MODEL_PATH),
        providers=["CPUExecutionProvider"],
    )
    app.state.model_load_time_ms = (perf_counter() - load_started) * 1000
    app.state.metrics = {"inference_calls": 0, "total_latency_ms": 0.0}
    app.state.metrics_lock = Lock()
    LOGGER.info(
        "Model loaded",
        extra={
            "model_version": MODEL_VERSION,
            "model_load_time_ms": app.state.model_load_time_ms,
        },
    )
    yield


app = FastAPI(
    title="Customer Churn ML API",
    version=API_VERSION,
    lifespan=lifespan,
)


@app.get("/health")
def health(request: Request) -> dict[str, str | float | bool]:
    if not hasattr(request.app.state, "model"):
        raise HTTPException(status_code=503, detail="Model is not loaded")
    return {
        "status": "ok",
        "model_loaded": True,
        "model_load_time_ms": request.app.state.model_load_time_ms,
    }


@app.get("/version")
def version() -> dict[str, str]:
    return {"api_version": API_VERSION, "model_version": MODEL_VERSION}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: CustomerFeatures, request: Request) -> PredictionResponse:
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    values = payload.model_dump()
    inputs = {
        model_input.name: np.asarray(
            [[values[model_input.name]]]
            if model_input.type == "tensor(string)"
            else [[np.nan if values[model_input.name] is None else values[model_input.name]]],
            dtype=object if model_input.type == "tensor(string)" else np.float32,
        )
        for model_input in model.get_inputs()
    }

    started = perf_counter()
    outputs = model.run(None, inputs)
    probability_outputs = [
        output
        for output in outputs
        if getattr(output, "ndim", 0) == 2 and output.shape[1] == 2
    ]
    if len(probability_outputs) != 1:
        raise RuntimeError("Could not identify the ONNX class-probability output.")
    churn_probability = float(probability_outputs[0][0, 1])
    prediction = "Yes" if churn_probability >= 0.5 else "No"
    latency_ms = (perf_counter() - started) * 1000

    with request.app.state.metrics_lock:
        request.app.state.metrics["inference_calls"] += 1
        request.app.state.metrics["total_latency_ms"] += latency_ms

    confidence = (
        churn_probability if prediction == "Yes" else 1.0 - churn_probability
    )
    LOGGER.info(
        "Prediction completed",
        extra={
            "prediction": prediction,
            "churn_probability": churn_probability,
            "inference_latency_ms": latency_ms,
            "model_version": MODEL_VERSION,
        },
    )
    return PredictionResponse(
        prediction=prediction,
        churn_probability=churn_probability,
        confidence=confidence,
        model_version=MODEL_VERSION,
    )


@app.get("/metrics")
def metrics(request: Request) -> dict[str, int | float]:
    with request.app.state.metrics_lock:
        inference_calls = request.app.state.metrics["inference_calls"]
        total_latency_ms = request.app.state.metrics["total_latency_ms"]

    average_latency_ms = (
        total_latency_ms / inference_calls if inference_calls else 0.0
    )
    return {
        "inference_calls": inference_calls,
        "average_latency_ms": average_latency_ms,
    }
