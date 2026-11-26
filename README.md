# DSCC-Azure-Event-Driven-ML

Event-driven Telecom Customer Churn prediction pipeline on Microsoft Azure, featuring serverless computing, distributed systems, observability and CI/CD.

> **Status:** the model (`feat/ml-training`, PR #18) and the inference API (`feat/ml-api`, PR #17) are proposed in open pull requests. They are **not merged into `main` nor deployed**. Issues #4 and #5 stay open until acceptance checks, merge and GHCR publication proof. The audit notes are not approvals.

## Model and training

The versioned churn model `1.0.0` is trained locally with:

```bash
py -3.12 model\train.py
```

- Authoritative input contract: [`model/features.json`](model/features.json) — **21 features**, `customerID` used only as an identifier, `Churn` never sent to the API.
- `TotalCharges` is coerced to numeric; blank cells are median-imputed inside the pipeline (no manual imputation before the split).
- Stratified 80/20 split, fixed seed `42`, logistic regression with `class_weight="balanced"`, decision threshold `0.5`.
- Metrics, baseline comparison and reproducibility evidence are produced in `model/metrics.json`; the protocol and the held-out test split are described in the PR #18 evidence (`model/TRAINING_EVIDENCE.md` on `feat/ml-training`).
- Dataset provenance/licence: IBM Telco Customer Churn sample (fictional customers), distributed via Kaggle as `blastchar/telco-customer-churn` ("Data files © Original Authors"); details in `model/DATASET.md` on `feat/ml-training`. No secret or real personal data.

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

Pull requests use the single workflow `.github/workflows/ci-ml.yml`: job `api-tests` (ruff, pytest, Docker build, <500 MB image gate) on `feat/ml-api`, and job `training-tests` (ruff + reproducibility tests) on `feat/ml-training`. Evidence: [CI run 45880949925](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45880949925). A **manual, opt-in** workflow `.github/workflows/publish-api.yml` can publish only a `preview-<commit-sha>` tag for branch testing; it never pushes `1.0.0` or `sha-<commit>`. Those release tags are reserved for the integrated workflow in PR #23 from `main`.

## Container

Build the multi-stage image from the repository root:

```bash
docker build -f api\Dockerfile -t churn-ml-api:1.0.0 .
```

The container runs as an unprivileged user and loads `/app/model/model-1.0.0.onnx`. [Run 45880950088](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45880950088) historically published `1.0.0` and `:sha-6fb916d19230cdd29fccffccdf3722704f1f8b25` (digest `sha256:7932660bde49aeeaffad67fd58f5609a80ab123b11b632d663a0f88adab3b3f8`) from this branch. That run is a **branch publication proof only**, not an authorisation to distribute or deploy; those tags must not be treated as the `main` release. The current workflow publishes only `preview-<commit-sha>` and is manual/opt-in. Azure Container Apps deployment, `curl` from the Internet, scale-to-zero and the release publication from `main` remain pending.

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` to enable Azure Monitor OpenTelemetry; without it, telemetry is disabled and the API still runs. Other optional variables: `API_VERSION`, `MODEL_VERSION`, `MODEL_PATH`.
