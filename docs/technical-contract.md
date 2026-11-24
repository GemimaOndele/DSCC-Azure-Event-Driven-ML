# DSCC — Technical Contract (DRAFT)

> **Status: PROPOSED — awaiting review by Gémima, Aminata and Elias.**
> This document consolidates the **Contrat** worksheet of `suivi_projet_groupe2.xlsx` and the mandatory interfaces in `PROJET_FR.pdf` (§4). It is *not* evidence of deployed services or finished code.
> Changes to this contract must be communicated to the team and submitted via pull request.

## 1. Scope and data flow

Telecom Customer Churn: upload a small CSV of clients into Azure Blob Storage (`input/`) → Event Grid `BlobCreated` → Function `dispatcher` → Storage Queue `inference-requests` → Function `worker` → FastAPI `POST /predict` → Blob `output/` + Cosmos DB or Table Storage → Function `GET /api/recent` → static dashboard in `$web`.

**Proposed Azure deployment:** one Python 3.12 Function App (v2 programming model, `function_app.py`) containing the three functions `dispatcher`, `worker`, and `recent`. **Pending team confirmation:** Flex Consumption with 512 MiB memory, subject to actual subscription/region availability; no resource has been deployed by this PR.

## 2. CSV input contract

- **Container:** `input/`
- **File type:** `.csv`
- **Proposed maximum file size:** `1 MiB` (team choice in the Excel workbook; not an imposed threshold from the instructor).
- **Implemented schema as of 24 Nov (PRs #17/#18):** `customerID` as an identifier **plus 21 model inputs**. The current API Pydantic model accepts the following 21 names; this list is **not yet an approved integration contract**:
  - **Categorical (15):** `gender`, `Partner`, `Dependents`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`.
  - **Numeric (6):** `SeniorCitizen`, `tenure`, `MonthlyCharges`, `TotalCharges`, `numAdminTickets`, `numTechTickets`.
- The earlier proposal of **19** inputs refers to a different schema and is **not compatible** with the current 21-input ONNX model. Elias and Aminata must approve the final list, validation and feature types. No `model/features.json` is present yet in PRs #17/#18; if it becomes the canonical source of truth, generate and test it against both training and API.
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
- `POST /predict`: **batch contract proposed, not implemented**. In PR #17 the API currently accepts **one flat 21-feature customer** per request and returns **one prediction**. Gémima, Aminata and Elias must agree whether the worker will batch requests or call the single-customer endpoint repeatedly (with retry/idempotency implications).
- `GET /metrics`: request count and average inference latency.

### Proposed `POST /predict` batch request (NOT supported by PR #17; illustrative incomplete row)

```json
{"rows": [{"customerID": "7590-VHVEG", "gender": "Female", "tenure": 1}]}
```

*The final request **must** also carry the approved required model features.*

### Proposed `POST /predict` batch response (NOT supported by PR #17)

```json
{
  "model_version": "1.0.0",
  "latency_ms": 12.3,
  "predictions": [
    {"customerID": "7590-VHVEG", "churn_probability": 0.73, "label": 1}
  ]
}
```

**Current implementation (PR #17):** one customer in → `{"prediction":"Yes|No","churn_probability":0.73,"confidence":0.73,"model_version":"1.0.0"}` out. The CSV/queue worker must not assume the proposed `rows` shape until it has been implemented and reviewed. The Excel proposes probability threshold `0.5`. **Validate** the decision against held-out data and record its rationale.

At least three `pytest` scenarios: success (200), invalid input (422), missing body (422).

## 5. Worker, retries and persistence

- Worker calls the API with an explicit timeout, writes complete result JSON to `output/<blobName>.json`, and stores metadata in Cosmos DB.
- **Proposed:** `maxDequeueCount = 5`. After failures, the queue-trigger mechanism should route to `inference-requests-poison`; reproduce a failure and keep evidence. Confirm actual Functions queue-trigger configuration in implementation.
- Record the reason for failed requests; retries must not duplicate inference metadata. **To decide before integration:** HTTP 422 (permanent schema/validation error) versus 429/500/503/timeouts (possibly transient, retry under bounded policy), API call timeout, per-row versus whole-file rejection, and behavior after a successful inference but failed persistence.
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

## 8. Integration discrepancies to resolve before approval

| Subject | Current implementation / observation (24 Nov 2026) | Decision required |
|---|---|---|
| Feature count | Training PR #18 and FastAPI PR #17 use **21** inputs, including two ticket counters; initial draft said 19 | Confirm 21 as the canonical version or change both implementations and regenerate model |
| Model identity | `model/model-1.0.0.onnx` exists in both #17 and #18 with **identical Git blob SHA** (`2fc9e022b7029f293bdc3a471f68a91f4d7e57ec`) | Select the model-training lot as the long-term source of the ONNX artifact; verify compatibility after sequential merges |
| API interface | PR #17 implements one customer per call; this contract proposes `rows` batch | Agree on batch semantics and response format, or revise worker design for repeated single-item calls |
| Cloud shape | One Function App / 3 Functions proposed, Python 3.12 | Confirm Flex Consumption **512 MiB**, region/quotas before Azure deployment |
| Queue errors | Five retries and poison queue proposed | Agree on HTTP permanent/transient classification, timeout and idempotent writes |
| CSV and persistence | 1 MiB cap and Blob ETag dedupe proposed | Confirm row-level failure policy, output JSON, Cosmos metadata, safe stable ID |
| Documentation and source data | Dataset `Customer_Churn_Dataset.xlsx` is committed by #18 | Confirm provenance/licence and report citation; keep public data only |

**Implementation status:** The model and API are in open PRs, **not yet merged to `main`**. The final decision belongs to the team; this document records observed differences without silently approving an incompatible change.

## 9. Approval checklist

- [ ] Gémima verifies file/queue/DB naming, object schema and status conventions.
- [ ] Elias confirms the **21 input features (versus previous 19)**, types, optional `TotalCharges`, ONNX artifact and exact model response; add a canonical feature schema if chosen.
- [ ] Aminata confirms dispatcher/worker, batch versus single-customer API contract, retry/error policy, rejection, timeout and idempotency.
- [ ] The three reviewers agree on the API request/response interface, probability threshold, error semantics and exceptions.
- [ ] Update this document through a reviewed Pull Request before implementing incompatible changes.

**Related GitHub issues:** #2 #4 #5 #6 #7 #9 #10.
