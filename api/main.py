import logging
import math
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Annotated, AsyncGenerator, Literal

import numpy as np
import onnxruntime
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


API_VERSION = os.getenv("API_VERSION", "1.0.0")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.1.0")
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
# Contract #14: a 1 MiB CSV cannot hold more rows than this; the cap protects
# the API from unbounded batches coming from the dispatcher/worker.
MAX_BATCH_ROWS = 10_000
MAX_STRING_LENGTH = 64
MAX_REQUEST_BYTES = 8 * 1024 * 1024
DECISION_THRESHOLD = 0.5
NON_FINITE_JSON = re.compile(rb":\s*(?:-?Infinity|NaN)(?=\s*[,}\]]|\s*$)")
LOGGER = logging.getLogger("dscc.ml_api")

# --- Custom metrics (issue #10, R4) -------------------------------------------
# OpenTelemetry instruments exported by azure-monitor-opentelemetry to the
# Application Insights `customMetrics` table (AppMetrics in Log Analytics).
# The proxy meter binds to the provider created by configure_azure_monitor()
# at startup; without a connection string the calls are no-ops.
# Attributes stay low-cardinality (endpoint, model version, error reason):
# the file name goes to logs/spans only, never to metric dimensions.
METER = metrics.get_meter("dscc.ml_api")
INFERRED_ROWS = METER.create_counter(
    "inferred_rows",
    unit="1",
    description="Client rows scored by the model (a batch of n rows adds n).",
)
INFERENCE_REQUESTS = METER.create_counter(
    "inference_requests",
    unit="1",
    description="Successful prediction HTTP calls (a batch counts as one).",
)
INFERENCE_LATENCY = METER.create_histogram(
    "inference_latency_ms",
    unit="ms",
    description="ONNX model execution time per prediction call.",
)
INFERENCE_ERRORS = METER.create_counter(
    "inference_errors",
    unit="1",
    description="Rejected (422) or failed prediction calls, by reason.",
)
PREDICT_PATHS = frozenset({"/predict", "/predict/batch"})
FILE_HEADER = "x-dscc-blob"  # sent by the worker (functions/src/api_client.py)
MAX_FILE_NAME_LENGTH = 256

YesNo = Literal["Yes", "No"]
NoInternetService = Literal["No", "Yes", "No internet service"]


class CustomerFeatures(BaseModel):
    """One client row: customerID is an identifier, the other 19 fields are model inputs.

    The case workbook also carries numAdminTickets/numTechTickets, but their
    availability before Churn is not documented. They are rejected (extra='forbid')
    so the API cannot silently send them to the 1.1.0 ONNX model.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    customerID: Annotated[
        str, Field(min_length=1, max_length=MAX_STRING_LENGTH, pattern=r"^[A-Za-z0-9._-]+$")
    ] | None = None
    gender: Literal["Female", "Male"]
    SeniorCitizen: Annotated[int, Field(ge=0, le=1)]
    Partner: YesNo
    Dependents: YesNo
    tenure: Annotated[int, Field(ge=0, le=120)]
    PhoneService: YesNo
    MultipleLines: Literal["No", "Yes", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: NoInternetService
    OnlineBackup: NoInternetService
    DeviceProtection: NoInternetService
    TechSupport: NoInternetService
    StreamingTV: NoInternetService
    StreamingMovies: NoInternetService
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal[
        "Bank transfer (automatic)",
        "Credit card (automatic)",
        "Electronic check",
        "Mailed check",
    ]
    MonthlyCharges: Annotated[float, Field(ge=0, le=10_000)]
    TotalCharges: Annotated[float | None, Field(ge=0, le=1_000_000)] = None

    @field_validator("MonthlyCharges", "TotalCharges")
    @classmethod
    def finite_numbers(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Numeric fields must be finite")
        return value

    @model_validator(mode="after")
    def no_control_characters(self) -> "CustomerFeatures":
        for name, value in self.model_dump().items():
            if isinstance(value, str) and any(ord(character) < 32 for character in value):
                raise ValueError(f"{name} contains control characters")
        return self


class PredictionResponse(BaseModel):
    prediction: Literal["No", "Yes"]
    churn_probability: float
    confidence: float
    model_version: str


class BatchPrediction(BaseModel):
    customerID: str | None = None
    prediction: Literal["No", "Yes"]
    label: Literal[0, 1]
    churn_probability: float
    confidence: float


class BatchSummary(BaseModel):
    rows: int
    atRisk: int
    avgChurnProbability: float
    threshold: float
    model_version: str


class BatchRequest(BaseModel):
    """Contract #14 multi-client payload: one CSV row per item in `rows`."""

    model_config = ConfigDict(extra="forbid")
    rows: list[CustomerFeatures] = Field(min_length=1, max_length=MAX_BATCH_ROWS)


class BatchResponse(BaseModel):
    model_version: str
    latency_ms: float
    predictions: list[BatchPrediction]
    summary: BatchSummary


def _configure_telemetry() -> bool:
    """Enable Azure Monitor OpenTelemetry when a connection string is set.

    Must run BEFORE `app = FastAPI(...)`: the distro instruments FastAPI by
    patching the class, so an app created earlier (e.g. configuring inside
    the lifespan) never gets the request middleware and the Application
    Insights `requests` table stays empty.
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return False
    configure_azure_monitor(
        connection_string=connection_string,
        logger_name=LOGGER.name,
    )
    return True


TELEMETRY_ENABLED = _configure_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if TELEMETRY_ENABLED:
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
    app.state.metrics = {
        "inference_calls": 0,
        "inferred_rows": 0,
        "total_latency_ms": 0.0,
    }
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
if TELEMETRY_ENABLED:
    # Explicit instrumentation: `from fastapi import FastAPI` above binds the
    # original class before the distro patches it, so automatic FastAPI
    # instrumentation would silently skip this app. /health is excluded to keep
    # probe traffic out of the 0.2 GB/day Log Analytics cap.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")


def _validation_safe(value: object) -> object:
    """Render Pydantic errors JSON-serialisable: no inf/nan, no raw objects."""
    if isinstance(value, float):
        return value if math.isfinite(value) else "non-finite"
    if isinstance(value, dict):
        return {key: _validation_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_validation_safe(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # JSONResponse uses allow_nan=False. An unsanitised inf/nan in a validation
    # error (e.g. 1e999 decoded as inf) would turn the expected 422 into a 500.
    _record_error(request.url.path, "validation")
    return JSONResponse(
        status_code=422, content={"detail": _validation_safe(exc.errors())}
    )


@app.middleware("http")
async def guard_json_body(request: Request, call_next):
    """Reject oversized bodies and non-finite JSON numbers before validation.

    Pydantic would otherwise echo NaN/Infinity in its 422 payload, which is not
    valid JSON and turns the rejection into a 500.
    """
    if request.method in {"POST", "PUT", "PATCH"} and request.headers.get(
        "content-type", ""
    ).startswith("application/json"):
        declared_size = request.headers.get("content-length")
        if declared_size and int(declared_size) > MAX_REQUEST_BYTES:
            _record_error(request.url.path, "too_large")
            return JSONResponse(
                status_code=413, content={"detail": "Request body is too large"}
            )
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES:
            _record_error(request.url.path, "too_large")
            return JSONResponse(
                status_code=413, content={"detail": "Request body is too large"}
            )
        if NON_FINITE_JSON.search(body):
            _record_error(request.url.path, "validation")
            return JSONResponse(
                status_code=422,
                content={"detail": "Non-finite JSON numbers are not allowed"},
            )
    return await call_next(request)


def _run_model(
    model: onnxruntime.InferenceSession, rows: list[CustomerFeatures]
) -> tuple[np.ndarray, float]:
    values_by_row = [row.model_dump() for row in rows]
    inputs = {
        model_input.name: np.asarray(
            [
                [np.nan if row[model_input.name] is None else row[model_input.name]]
                for row in values_by_row
            ],
            dtype=object if model_input.type == "tensor(string)" else np.float32,
        )
        for model_input in model.get_inputs()
    }

    started = perf_counter()
    outputs = model.run(None, inputs)
    latency_ms = (perf_counter() - started) * 1000
    probability_outputs = [
        output
        for output in outputs
        if getattr(output, "ndim", 0) == 2 and output.shape[1] == 2
    ]
    if len(probability_outputs) != 1:
        raise RuntimeError("Could not identify the ONNX class-probability output.")
    probabilities = probability_outputs[0][:, 1]
    if probabilities.shape[0] != len(rows):
        raise RuntimeError("ONNX output does not contain one probability per client.")
    return probabilities, latency_ms


def _prediction(probability: float, customer_id: str | None) -> BatchPrediction:
    prediction = "Yes" if probability >= DECISION_THRESHOLD else "No"
    confidence = probability if prediction == "Yes" else 1.0 - probability
    return BatchPrediction(
        customerID=customer_id,
        prediction=prediction,
        label=int(prediction == "Yes"),
        churn_probability=float(probability),
        confidence=float(confidence),
    )


def _record_metrics(
    request: Request, latency_ms: float, rows: int, endpoint: str
) -> None:
    """Count HTTP calls and the clients actually inferred (R4 monitoring).

    The in-memory counters feed GET /metrics (per replica, reset at scale to
    zero); the OpenTelemetry instruments feed Application Insights, which keeps
    the history across replicas for KQL and alerts.
    """
    with request.app.state.metrics_lock:
        request.app.state.metrics["inference_calls"] += 1
        request.app.state.metrics["inferred_rows"] += rows
        request.app.state.metrics["total_latency_ms"] += latency_ms
    attributes = {"endpoint": endpoint, "model_version": MODEL_VERSION}
    INFERENCE_REQUESTS.add(1, attributes)
    INFERRED_ROWS.add(rows, attributes)
    INFERENCE_LATENCY.record(latency_ms, attributes)


def _record_error(path: str, reason: str) -> None:
    """Count rejected/failed prediction calls; other routes are ignored."""
    if path in PREDICT_PATHS:
        INFERENCE_ERRORS.add(
            1, {"endpoint": path, "reason": reason, "model_version": MODEL_VERSION}
        )


def _scored(
    request: Request, rows: list[CustomerFeatures], endpoint: str
) -> tuple[np.ndarray, float]:
    try:
        return _run_model(_loaded_model(request), rows)
    except HTTPException:
        _record_error(endpoint, "model_not_loaded")
        raise
    except Exception:
        _record_error(endpoint, "model_error")
        raise


def _file_name(request: Request) -> str | None:
    """Blob name sent by the worker, sanitised, attached to the request span.

    It lands in requests.customDimensions["dscc.file_name"] so KQL can rank
    the slowest files without adding a high-cardinality metric dimension.
    """
    raw = request.headers.get(FILE_HEADER)
    if not raw:
        return None
    name = "".join(ch for ch in raw if ch.isprintable())[:MAX_FILE_NAME_LENGTH]
    if name:
        trace.get_current_span().set_attribute("dscc.file_name", name)
    return name or None


def _loaded_model(request: Request) -> onnxruntime.InferenceSession:
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")
    return model


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
    """Unit inference, kept for backward compatibility and local worker calls."""
    probabilities, latency_ms = _scored(request, [payload], "/predict")
    result = _prediction(probabilities[0], payload.customerID)
    _record_metrics(request, latency_ms, rows=1, endpoint="/predict")
    LOGGER.info(
        "Prediction completed",
        extra={
            "prediction": result.prediction,
            "churn_probability": result.churn_probability,
            "inference_latency_ms": latency_ms,
            "model_version": MODEL_VERSION,
        },
    )
    return PredictionResponse(
        prediction=result.prediction,
        churn_probability=result.churn_probability,
        confidence=result.confidence,
        model_version=MODEL_VERSION,
    )


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(payload: BatchRequest, request: Request) -> BatchResponse:
    """Batch inference for a multi-client CSV (contract #14, option A)."""
    file_name = _file_name(request)
    probabilities, latency_ms = _scored(request, payload.rows, "/predict/batch")
    predictions = [
        _prediction(probabilities[index], row.customerID)
        for index, row in enumerate(payload.rows)
    ]
    summary = BatchSummary(
        rows=len(predictions),
        atRisk=sum(prediction.label for prediction in predictions),
        avgChurnProbability=float(np.mean(probabilities)),
        threshold=DECISION_THRESHOLD,
        model_version=MODEL_VERSION,
    )
    _record_metrics(
        request, latency_ms, rows=len(payload.rows), endpoint="/predict/batch"
    )
    LOGGER.info(
        "Batch prediction completed",
        extra={
            "file_name": file_name or "",
            "rows": summary.rows,
            "at_risk": summary.atRisk,
            "inference_latency_ms": latency_ms,
            "model_version": MODEL_VERSION,
        },
    )
    return BatchResponse(
        model_version=MODEL_VERSION,
        latency_ms=latency_ms,
        predictions=predictions,
        summary=summary,
    )


@app.get("/metrics")
def metrics(request: Request) -> dict[str, int | float]:
    with request.app.state.metrics_lock:
        inference_calls = request.app.state.metrics["inference_calls"]
        inferred_rows = request.app.state.metrics["inferred_rows"]
        total_latency_ms = request.app.state.metrics["total_latency_ms"]

    average_latency_ms = (
        total_latency_ms / inference_calls if inference_calls else 0.0
    )
    return {
        "inference_calls": inference_calls,
        "inferred_rows": inferred_rows,
        "average_latency_ms": average_latency_ms,
    }
