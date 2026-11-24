# DSCC — Technical Contract (DRAFT)

> **Status: PROPOSED — awaiting review by Gémima, Aminata and Elias.**
> This document consolidates the **Contrat** worksheet of `suivi_projet_groupe2.xlsx` and the mandatory interfaces in `PROJET_FR.pdf` (§4). It is *not* evidence of deployed services or finished code.
> Changes to this contract must be communicated to the team and submitted via pull request.

## 1. Scope and data flow

Telecom Customer Churn: upload a small CSV of clients into Azure Blob Storage (`input/`) → Event Grid `BlobCreated` → Function `dispatcher` → Storage Queue `inference-requests` → Function `worker` → FastAPI `POST /predict/batch` → Blob `output/` + Cosmos DB or Table Storage → Function `GET /api/recent` → static dashboard in `$web`.

**Proposed Azure deployment:** one Python 3.12 Function App (v2 programming model, `function_app.py`) containing the three functions `dispatcher`, `worker`, and `recent`. **Pending team confirmation:** Flex Consumption with 512 MiB memory, subject to actual subscription/region availability; no resource has been deployed by this PR.

## 2. CSV input contract

- **Container:** `input/`
- **File type:** `.csv`
- **Proposed maximum file size:** `1 MiB` (team choice, not an imposed threshold from the instructor). The API currently caps JSON requests at 8 MiB and batches at 10,000 rows; the dispatcher should enforce the **stricter CSV file limit** independently.
- **Implemented schema as of 24 Nov (PRs #17/#18):** `customerID` as an identifier **plus 21 model inputs**. The current API Pydantic model accepts the following 21 names; this list is **not yet an approved integration contract**:
  - **Categorical (15):** `gender`, `Partner`, `Dependents`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`.
  - **Numeric (6):** `SeniorCitizen`, `tenure`, `MonthlyCharges`, `TotalCharges`, `numAdminTickets`, `numTechTickets`.
- The earlier proposal of **19** inputs refers to a different schema and is **not compatible** with the current 21-input ONNX model. Elias and Aminata must approve the final list, validation and feature types. Both #17 and #18 contain compatible 21-input schemas, but their `source_dataset` metadata now differs; reconcile before integration, and their automated tests check it. Approval by the team is still required.
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
- `POST /predict`: **implemented by PR #17**, single-customer inference with the 21 model inputs and optional `customerID`, returning one prediction.
- `POST /predict/batch`: **implemented by PR #17** with `{"rows":[...]}` (one row per client); returns `predictions` per client and a global `summary`. This is the **proposed canonical worker route** (option A from Elias, supported in Aminata's review), pending team sign-off and merge.
- `GET /metrics`: HTTP request count `inference_calls`, count of predicted client rows `inferred_rows` and `average_latency_ms`. Omar (R4) confirmed `inferred_rows` for KQL/alerts in his #17 review; this endpoint is currently submitted in PR #17.

### `POST /predict/batch` request (shape implemented in PR #17; illustrative incomplete row)

```json
{"rows": [{"customerID": "7590-VHVEG", "gender": "Female", "tenure": 1}]}
```

*The final request **must** also carry the approved required model features.*

### `POST /predict/batch` response (schema implemented in PR #17; example values illustrative)

```json
{
  "model_version": "1.0.0",
  "latency_ms": 12.3,
  "predictions": [
    {"customerID": "7590-VHVEG", "prediction": "Yes", "label": 1, "churn_probability": 0.73, "confidence": 0.73}
  ],
  "summary": {
    "rows": 1,
    "atRisk": 1,
    "avgChurnProbability": 0.73,
    "threshold": 0.5,
    "model_version": "1.0.0"
  }
}
```

**Current implementation (PR #17, not merged):** `POST /predict` accepts one customer and returns `{ "prediction": "Yes|No", "churn_probability": 0.73, "confidence": 0.73, "model_version": "1.0.0" }`. **Batch** is now implemented at the separate `/predict/batch` route, with 13 API tests and a green `api-tests` job. The threshold is `0.5` in the current 21-feature model; reviewers should validate it and its held-out evidence before declaring a frozen interface.

Current PR #17 reports 13 API pytest cases, including multi-row batch, invalid/empty fields, numeric overflow (`1e999` → 422), and metrics accumulation, with a green GitHub Actions `api-tests` job including Docker build. This is a reviewable code contribution, **not yet merged or deployed**.

## 5. Worker, retries and persistence

- Worker calls the API with an explicit timeout, writes complete result JSON to `output/<blobName>.json`, and stores metadata in Cosmos DB.
- **Proposed:** `maxDequeueCount = 5`. After failures, the queue-trigger mechanism should route to `inference-requests-poison`; reproduce a failure and keep evidence. Confirm actual Functions queue-trigger configuration in implementation.
- **Proposed error policy (awaiting R2 approval):** HTTP 422 or permanent schema errors → record rejection reason and do not retry blindly. HTTP 429/500/503 and timeouts → bounded retries (maximum five queue deliveries), then poison message and an incident record. Set and test a concrete HTTP timeout in the worker. Retrying after a successful inference must not duplicate output or Cosmos metadata; use `blobName` + `etag` as the idempotency key.
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
| Feature count | PRs #17 and #18 use **21** inputs and share `model/features.json`; `customerID` is an identifier, not a feature | Confirm as an explicit team integration decision, including the provenance of `numAdminTickets`/`numTechTickets` |
| Model identity | `model/model-1.0.0.onnx` exists in both #17 and #18 with **identical Git blob SHA** (`2fc9e022b7029f293bdc3a471f68a91f4d7e57ec`) | Select the model-training lot as the long-term source of the ONNX artifact; verify compatibility after sequential merges |
| API interface | PR #17 now implements `/predict` **unitaire** and `/predict/batch` accepting `rows` with `predictions` + `summary` | **Confirm this separate batch URL** with R2 and enforce it in the worker; retain the unit endpoint for local use |
| Cloud shape | One Function App / 3 Functions proposed, Python 3.12 | Confirm Flex Consumption **512 MiB**, region/quotas before Azure deployment |
| Queue errors | Five retries and poison queue proposed | Agree on HTTP permanent/transient classification, timeout and idempotent writes |
| CSV and persistence | 1 MiB cap and Blob ETag dedupe proposed | Confirm row-level failure policy, output JSON, Cosmos metadata, safe stable ID |
| Documentation and source data | PR #18 at `5c7eb97` removes the workbook and test split from the current tree and retrieves the source with SHA-256 verification; permission for automated educational use and historical copies remain to be checked | Confirm source permission and team decision on temporal leakage before merging #18 |

**Implementation status:** The model and API are in open PRs, **not yet merged to `main`**. The final decision belongs to the team; this document records observed differences without silently approving an incompatible change.

## 9. Approval checklist

- [ ] Gémima verifies file/queue/DB naming, object schema and status conventions.
- [ ] Elias confirms the **21 input features (versus previous 19)**, types, optional `TotalCharges`, ONNX artifact and exact model response; add a canonical feature schema if chosen.
- [ ] Aminata confirms the worker's use of `POST /predict/batch`, retry/error policy, rejection, timeout and idempotency.
- [ ] The three reviewers agree on `POST /predict/batch` and the response `predictions`/`summary`, probability threshold, error semantics, queue poison strategy and exceptions.
- [ ] Update this document through a reviewed Pull Request before implementing incompatible changes.

**Related GitHub issues:** #2 #4 #5 #6 #7 #9 #10.


## 10. Integration decisions proposed for final R2/R1 review (24 Nov 2026)

These values reflect the current `feat/event-pipeline` implementation, not a new claim of team approval or deployed behavior.

- Worker HTTP connect timeout: **2 s**; read timeout: **10 s** (`API_CONNECT_TIMEOUT_SECONDS`, `API_READ_TIMEOUT_SECONDS`). These are separate limits, not a total wall-clock deadline. Confirm with R2 and test timeout/retry behavior.
- CSV: UTF-8 (BOM accepted), comma separator, canonical ordered header, no extra columns, blank rows ignored, decimal point, maximum 1 MiB and 10,000 rows. `customerID` required in CSV (1–64 characters); empty `TotalCharges` maps to null. Reject the entire file on any invalid nonblank row; no partial scoring. R2 must ensure permanent CSV errors in the worker are rejected rather than retried, including when content changes after dispatch.
- Rejection JSON currently implemented: `{"blobName":"batch_01.csv","reason":"validation error","status":"rejected"}`; reason limited to 2,000 characters. Confirm original-file retention and avoid sensitive values in logs.
- Cosmos ID currently implemented: sanitized filename stem (max 40 characters), hyphen, first 16 hex characters of SHA-256 of UTF-8 `blobName|etag`. Partition key `/fileName`. Verify conditional reads against the event ETag, concurrent duplicate delivery and distinct output versions; the digest alone does not guarantee exactly-once inference.
- R1: 21 features and threshold 0.5 remain provisional for the academic demo; the two ticket counters have no demonstrated pre-churn availability. Omar's ablation is reported in #18. Do not freeze the schema or claim production validity until the team chooses 21 or 19 features and confirms dataset usage rights. If 19, retrain and update API, worker, ONNX, tests and metrics together.
- Integration: Omar identified sequential merge conflicts in `README.md` and `model/features.json` between #17/#18. Resolve on a reviewed branch and rerun both test suites and Docker build; do not merge either in isolation until the dataset decision is recorded.
- R4: Omar confirmed `inferred_rows` for KQL; #19 dashboard consumes `{count,limit,results}` from `/api/recent`. Real Azure evidence remains pending.
