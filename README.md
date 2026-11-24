# DSCC-Azure-Event-Driven-ML

Event-driven Telecom Customer Churn prediction pipeline on Microsoft Azure, featuring serverless computing, distributed systems, observability and CI/CD.

> **Status:** the model (`feat/ml-training`, PR #18) and the inference API (`feat/ml-api`, PR #17) are proposed in open pull requests. They are **not merged into `main` nor deployed**. Issues #4 and #5 stay open until acceptance checks, merge and GHCR publication proof. The audit notes are not approvals.

## Model and training

The versioned churn model `1.0.0` is trained locally with:

```bash
py -3.12 model\prepare_data.py   # vérification SHA-256, données non commitées
py -3.12 model\train.py
```

- Authoritative input contract: [`model/features.json`](model/features.json) — **21 features**, `customerID` used only as an identifier, `Churn` never sent to the API.
- `TotalCharges` is coerced to numeric; blank cells are median-imputed inside the pipeline (no manual imputation before the split).
- Stratified 80/20 split, fixed seed `42`, logistic regression with `class_weight="balanced"`, decision threshold `0.5`.
- Metrics, baseline comparison and reproducibility evidence are produced in `model/metrics.json`; the protocol is described in the PR #18 evidence (`model/TRAINING_EVIDENCE.md` on `feat/ml-training`). The held-out split is generated locally in `model/test_split.csv` and is **not committed**.
- Dataset provenance/licence: the DSCC case workbook is **not redistributed**; `model/prepare_data.py` fetches it from its public source with a pinned SHA-256. The 21 base columns come from IBM Telco Customer Churn (Apache-2.0); the two ticket counters are supplied by the case material. Details and redistribution terms: `model/DATASET.md` on `feat/ml-training`. No secret or real personal data.

## Inference API

Install `api\requirements-dev.txt` and start locally:

```bash
py -3.12 -m uvicorn api.main:app --reload
```

Endpoints: `GET /health`, `GET /version`, `POST /predict` (one client), `POST /predict/batch` (multi-client CSV) and `GET /metrics`.

Unit request (backward compatible with PR #17):

```json
{"customerID": "7590-VHVEG", "gender": "Female", "SeniorCitizen": 0, "...": "20 other model features"}
```

Batch request — the contract #14 option A chosen for the dispatcher/worker. Each item is one CSV row; `customerID` is echoed in the response:

```json
{
  "rows": [
    {"customerID": "7590-VHVEG", "gender": "Female", "SeniorCitizen": 0, "...": "20 other model features"},
    {"customerID": "5575-GNVDE", "gender": "Male", "SeniorCitizen": 0, "...": "20 other model features"}
  ]
}
```

```json
{
  "model_version": "1.0.0",
  "latency_ms": 12.3,
  "predictions": [
    {"customerID": "7590-VHVEG", "prediction": "Yes", "label": 1, "churn_probability": 0.73, "confidence": 0.73}
  ],
  "summary": {"rows": 50, "atRisk": 12, "avgChurnProbability": 0.31, "threshold": 0.5, "model_version": "1.0.0"}
}
```

`GET /metrics` reports `inference_calls` (**HTTP inference requests**, one batch = one call), `inferred_rows` (**clients actually predicted**, `len(rows)` per batch; name to be confirmed with Omar for KQL/alerts) and average ONNX latency. Input hardening: unknown/extra fields and unknown categories are rejected with `422`, numeric ranges and finite values are enforced, blank strings and control characters are rejected, and batches are capped at `MAX_BATCH_ROWS = 10000` (larger than a 1 MiB CSV can hold per contract #14).

## Tests and CI

```bash
py -3.12 -m pytest api\tests -q
py -3.12 -m pytest model\tests -q   # on feat/ml-training
```

Pull requests run the workflows `.github/workflows/ci-ml-api.yml` (pytest + Docker build) and `.github/workflows/ci-ml-training.yml` (pytest + reproducible retraining). Local results and the Docker image size are recorded in the PR descriptions.

## Container

Build the multi-stage image from the repository root:

```bash
docker build -f api\Dockerfile -t churn-ml-api:1.0.0 .
```

The container runs as an unprivileged user and loads `/app/model/model-1.0.0.onnx`. Publishing the image to GHCR is tracked by issue #8 and is **not** included in these PRs; issue #5 must not be closed before that proof exists.

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` to enable Azure Monitor OpenTelemetry; without it, telemetry is disabled and the API still runs. Other optional variables: `API_VERSION`, `MODEL_VERSION`, `MODEL_PATH`.
