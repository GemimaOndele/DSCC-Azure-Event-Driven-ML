# DSCC — Technical Contract (DRAFT)

> **Status: PROPOSED — awaiting review by Gémima, Aminata and Elias.**
> This document consolidates the **Contrat** worksheet of `suivi_projet_groupe2.xlsx` and the mandatory interfaces in `PROJET_FR.pdf` (§4). It is *not* evidence of deployed services or finished code.
> Changes to this contract must be communicated to the team and submitted via pull request.

## 1. Scope and data flow

Telecom Customer Churn: upload a small CSV of clients into Azure Blob Storage (`input/`) → Event Grid `BlobCreated` → Function `dispatcher` → Storage Queue `inference-requests` → Function `worker` → FastAPI `POST /predict` → Blob `output/` + Cosmos DB or Table Storage → Function `GET /api/recent` → static dashboard in `$web`.

One Python 3.12 Function App (v2 programming model, `function_app.py`) contains `dispatcher`, `worker`, and `recent`.

## 2. CSV input contract

- **Container:** `input/`
- **File type:** `.csv`
- **Proposed maximum file size:** `1 MiB` (team choice in the Excel workbook; not an imposed threshold from the instructor).
- **Required schema:** `customerID` plus the 19 features explicitly listed in `model/features.json` (to be generated/approved alongside the trained model).
- The target variable `Churn` must **not** be required by the inference API.
- `TotalCharges` preprocessing must match training.
- Invalid extension, excessive size, or missing mandatory columns → copy to `rejected/` and write `<blobName>.reason.json` with a human-readable rejection reason.

**Open decisions:** final features, per-column types, strict vs tolerant extra columns, invalid-row behavior, blank-line policy, decimal encoding and whether batch size is capped separately.

## 3. Queue message

Storage queue: `inference-requests`. Its poison queue is `inference-requests-poison`.

```json
{
  "blobName": "batch_01.csv",
  "etag": "0x8DC...",
  "size": 12345,
  "enqueuedAt": "2026-11-20T10:00:00Z"
}
```

`blobName` and `etag` jointly identify a particular content version. A worker must use idempotent writes/upsert and should reuse HTTP clients.

## 4. API endpoints

- `GET /health`: readiness and model load time.
- `GET /version`: API version and semantic model version.
- `POST /predict`: batch inference using a Pydantic-validated request.
- `GET /metrics`: request count and average inference latency.

### Example `POST /predict` request (illustrative, incomplete row)

```json
{"rows": [{"customerID": "7590-VHVEG", "gender": "Female", "tenure": 1}]}
```

*The final request **must** also carry the approved required model features.*

### Example `POST /predict` response

```json
{
  "model_version": "1.0.0",
  "latency_ms": 12.3,
  "predictions": [
    {"customerID": "7590-VHVEG", "churn_probability": 0.73, "label": 1}
  ]
}
```

The Excel proposes a probability threshold `0.5`. **Validate** it against held-out data; record the decision and rationale.

At least three `pytest` scenarios: success (200), invalid input (422), missing body (422).

## 5. Worker, retries and persistence

- Worker calls the API with an explicit timeout, writes complete result JSON to `output/<blobName>.json`, and stores metadata in Cosmos DB.
- `maxDequeueCount = 5`. After failures, move to `inference-requests-poison`; reproduce a failure and keep evidence.
- Record the reason for failed requests; retries must not duplicate inference metadata.
- Azure Cosmos DB (preferred if free tier is available): database `pipeline`, container `inferences`, partition key `/fileName`. **Fallback:** Azure Table Storage.

Example **metadata** from the Excel:

```json
{
  "id": "<blobName>-<etag>",
  "fileName": "batch_01.csv",
  "timestamp": "2026-11-20T10:00:05Z",
  "rows": 50,
  "atRisk": 12,
  "avgChurnProbability": 0.31,
  "modelVersion": "1.0.0",
  "durationMs": 480,
  "status": "ok"
}
```

**Open decision:** ensure the `id` representation safely handles Blob names and ETags and stays stable across retries.

## 6. Dashboard and monitoring

- `GET /api/recent` returns the 20 latest results (JSON), with CORS restricted to the static site's origin.
- Static HTML/JS on Blob Storage `$web`, with at least one Chart.js visualization and auto-refresh every **30 seconds**.
- OpenTelemetry through `azure-monitor-opentelemetry` for the API; explicit workspace-based App Insights and Log Analytics capped at **0.2 GB/day**.
- At least two custom metrics: inference count and model latency; three KQL queries and one triggered alert.

## 7. Environment, security and cost constraints

Proposed shared variable names in the Excel: `MODEL_API_URL`, `COSMOS_ENDPOINT`, `STORAGE_ACCOUNT`.

- No passwords, storage keys, credentials or connection strings in the repository.
- Deploy via GitHub Actions with OIDC and a user-assigned managed identity; restrict Contributor to the project resource group.
- Azure for Students: one selected integration subscription; budget **USD 25 maximum**, target **under USD 5**; verify region compatibility before provisioning.
- No VM, GPU or AKS. Use local Docker/Azurite/Functions Core Tools before Azure services are available.

## 8. Approval checklist

- [ ] Gémima verifies file/queue/DB naming, object schema and status conventions.
- [ ] Elias confirms `features.json`, feature types, expected validation and model response.
- [ ] Aminata confirms dispatcher/worker, retry, rejection and idempotency contracts.
- [ ] The three reviewers agree on the threshold and exceptions.
- [ ] Update this document through a reviewed Pull Request before implementing incompatible changes.

**Related GitHub issues:** #2 #4 #5 #6 #7 #9 #10.
