# DSCC — Technical Contract (DRAFT)

> **Status: PROPOSED — 27 Nov: R1/R4 selected 19 inputs and model 1.1.0; this is the current integration target, not a fully approved contract. Dataset/artifact rights, independent re-review and cloud acceptance remain pending.**
> This document consolidates the **Contrat** worksheet of `suivi_projet_groupe2.xlsx` and the mandatory interfaces in `PROJET_FR.pdf` (§4). It is *not* evidence of deployed services or finished code.
> Changes to this contract must be communicated to the team and submitted via pull request.

## 1. Scope and data flow

Telecom Customer Churn: upload a small CSV of clients into Azure Blob Storage (`input/`) → Event Grid `BlobCreated` → Function `dispatcher` → Storage Queue `inference-requests` → Function `worker` → FastAPI `POST /predict/batch` → Blob `output/` + Cosmos DB or Table Storage → Function `GET /api/recent` → static dashboard in `$web`.

**Proposed Azure deployment:** one Python 3.12 Function App (v2 programming model, `function_app.py`) containing the three functions `dispatcher`, `worker`, and `recent`. **Pending team confirmation:** Flex Consumption with 512 MiB memory, subject to actual subscription/region availability; no resource has been deployed by this PR.

## 2. CSV input contract

- **Container:** `input/`
- **File type:** `.csv`
- **Proposed maximum file size:** `1 MiB` (team choice, not an imposed threshold from the instructor). The API currently caps JSON requests at 8 MiB and batches at 10,000 rows; the dispatcher should enforce the **stricter CSV file limit** independently.
- **Integration target as of 27 Nov (PRs #17/#18):** `customerID` as an identifier **plus 19 model inputs** (15 categorical, 4 numeric); independent contract review remains required:
  - **Categorical (15):** `gender`, `Partner`, `Dependents`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`.
  - **Numeric (4):** `SeniorCitizen`, `tenure`, `MonthlyCharges`, `TotalCharges`.
- R1/R4 removed `numAdminTickets` and `numTechTickets` because their availability before churn is undocumented. Both the API and CSV parser must reject them as extra columns. This reduces temporal leakage risk, without proving past leakage. The historical 21-feature artifact is 1.0.0; the new target is 1.1.0.
- The target variable `Churn` must **not** be required by the inference API.
- `TotalCharges` preprocessing must match training.
- Invalid extension, excessive size, or missing mandatory columns → copy to `rejected/` and write `<blobName>.reason.json` with a human-readable rejection reason.

**Current R2 conventions:** exact ordered header, UTF-8/BOM, decimal point, reject extra columns and the entire invalid file, ignore blank lines, 1 MiB and 10,000 rows. Aminata confirmed these technically on 27 Nov; formal approval and cloud binding tests remain open.

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
- `POST /predict`: **implemented by PR #17**, single-customer inference with the 19 model inputs and optional `customerID`, returning one prediction.
- `POST /predict/batch`: **implemented by PR #17** with `{"rows":[...]}` (one row per client); returns `predictions` per client and a global `summary`. This is the **proposed canonical worker route** (option A from Elias, supported in Aminata's review), pending team sign-off and merge.
- `GET /metrics`: HTTP request count `inference_calls`, count of predicted client rows `inferred_rows` and `average_latency_ms`. Omar (R4) confirmed `inferred_rows` for KQL/alerts in his #17 review; this endpoint is currently submitted in PR #17.

- Worker correlation headers: `X-DSCC-Blob` and `X-DSCC-ETag`. PR #20 uses the blob name in the request span as `dscc.file_name`; never use blob names or ETags as metric dimensions.

### `POST /predict/batch` request (shape implemented in PR #17; illustrative incomplete row)

```json
{"rows": [{"customerID": "7590-VHVEG", "gender": "Female", "tenure": 1}]}
```

*The final request **must** also carry the approved required model features.*

### `POST /predict/batch` response (schema implemented in PR #17; example values illustrative)

```json
{
  "model_version": "1.1.0",
  "latency_ms": 12.3,
  "predictions": [
    {"customerID": "7590-VHVEG", "prediction": "Yes", "label": 1, "churn_probability": 0.73, "confidence": 0.73}
  ],
  "summary": {
    "rows": 1,
    "atRisk": 1,
    "avgChurnProbability": 0.73,
    "threshold": 0.5,
    "model_version": "1.1.0"
  }
}
```

**Current implementation (PR #17, not merged):** `POST /predict` accepts one customer and returns `{ "prediction": "Yes|No", "churn_probability": 0.73, "confidence": 0.73, "model_version": "1.1.0" }`. **Batch** is now implemented at the separate `/predict/batch` route, with telemetry and regression tests; confirm the latest 1.1.0 CI before release. The threshold is `0.5` in the current 19-feature model; reviewers should validate it and its held-out evidence before declaring a frozen interface.

PR #17 implemented the batch, numeric overflow, metrics accumulation and OTel tests on the previous model. Reverify them against 1.1.0; this is not yet a deployed release.

## 5. Worker, retries and persistence

- Worker calls the API with an explicit timeout and stores result JSON and Cosmos metadata. **Updated R2 proposal (#21, pending review):** create-only `output/<blobName>.<idempotencyKey>.json`, one immutable result per input version; this replaces the earlier unversioned path if the team approves it.
- **Proposed:** `maxDequeueCount = 5`. After failures, the queue-trigger mechanism should route to `inference-requests-poison`; reproduce a failure and keep evidence. Confirm actual Functions queue-trigger configuration in implementation.
- **Proposed error policy (awaiting R2 approval):** HTTP 422 or permanent schema errors → record rejection reason and do not retry blindly. HTTP 429/500/503 and timeouts → bounded retries (maximum five queue deliveries), then poison message and an incident record. Set and test a concrete HTTP timeout in the worker. Retrying after a successful inference must not duplicate output or Cosmos metadata; use `blobName` + `etag` as the idempotency key.
- Azure Cosmos DB (preferred if free tier is available): database `pipeline`, container `inferences`, partition key `/fileName`. **Fallback:** Azure Table Storage.

Example **metadata** from the Excel:

```json
{
  "id": "<sanitized-stem>-<first16-sha256-hex>",
  "fileName": "batch_01.csv",
  "timestamp": "2026-11-20T10:00:05Z",
  "rows": 50,
  "atRisk": 12,
  "avgChurnProbability": 0.31,
  "modelVersion": "1.1.0",
  "durationMs": 480,
  "status": "ok"
}
```

**Implemented in #21, pending approval:** sanitized filename stem (max 40 chars) + hyphen + first 16 hex SHA-256 characters of UTF-8 `blobName|etag`.

## 6. Dashboard and monitoring

- `GET /api/recent` returns the 20 latest results (JSON), with CORS restricted to the static site's origin.
- Static HTML/JS on Blob Storage `$web`, with at least one Chart.js visualization and auto-refresh every **30 seconds**.
- OpenTelemetry through `azure-monitor-opentelemetry` for the API; explicit workspace-based App Insights and Log Analytics capped at **0.2 GB/day**.
- Custom instruments proposed in #20: `inferred_rows` (counter), `inference_latency_ms` (histogram), `inference_requests` (successful prediction calls), and `inference_errors` (reason: `validation`, `too_large`, `model_error`, `model_not_loaded`). Dimensions: `endpoint`, `model_version`, and `reason` only for errors. Three KQL queries and one triggered alert remain required.
- Configure Azure Monitor before creating FastAPI or explicitly instrument the app; #20 implements explicit instrumentation and excludes `/health` to limit probe ingestion. Verify exported spans and metrics before acceptance.

## 7. Environment, security and cost constraints

Proposed shared variable names in the Excel: `MODEL_API_URL`, `COSMOS_ENDPOINT`, `STORAGE_ACCOUNT`.

- No passwords, storage keys, credentials or connection strings in the repository.
- Deploy via GitHub Actions with OIDC and a user-assigned managed identity; restrict Contributor to the project resource group.
- Azure for Students: Gémima confirms that both she and Aminata have sufficient credit, based on previously shared evidence. The owner subscription and France Central were selected in the Work setup evidence on #24; Aminata's account is fallback. Budget EUR 4/month with 20/50/80% alerts, total project ceiling **USD 25**, target **under USD 5**. Actual quotas and Free Tier eligibility still require verification.
- No VM, GPU or AKS. Use local Docker/Azurite/Functions Core Tools before Azure services are available.

## 8. Integration discrepancies to resolve before approval

| Subject | Current implementation / observation (27 Nov 2026) | Decision required |
|---|---|---|
| Feature count | PRs #17/#18 target **19** inputs, 15 categorical and 4 numeric; `customerID` is not a feature | R1/R4 selection recorded; coordinator and independent reviewer confirmation still required |
| Model identity | `model/model-1.1.0.onnx`, reported shared blob `09ee933f16731e7218189d19d7c3ab98162de34e` | Verify exact Git blob identity and integrated tests |
| API interface | PR #17 now implements `/predict` **unitaire** and `/predict/batch` accepting `rows` with `predictions` + `summary` | **Confirm this separate batch URL** with R2 and enforce it in the worker; retain the unit endpoint for local use |
| Cloud shape | One Function App / 3 Functions proposed, Python 3.12 | Confirm Flex Consumption **512 MiB**, region/quotas before Azure deployment |
| Queue errors | Five retries and poison queue proposed | Agree on HTTP permanent/transient classification, timeout and idempotent writes |
| CSV and persistence | 1 MiB cap and Blob ETag dedupe proposed | Confirm row-level failure policy, output JSON, Cosmos metadata, safe stable ID |
| Documentation and source data | PR #18 at `5c7eb97` removes the workbook and test split from the current tree and retrieves the source with SHA-256 verification; permission for automated educational use and historical copies remain to be checked | Confirm source and artifact permission before merging/releasing #18 |

**Implementation status:** The model and API are in open PRs, **not yet merged to `main`**. The final decision belongs to the team; this document records observed differences without silently approving an incompatible change.

## 9. Approval checklist

- [ ] Omar revalidates R4 after these changes (previous approval on `a20b1ba`).
- [ ] Gémima verifies file/queue/DB naming, object schema and status conventions.
- [ ] Elias re-reviews the 19-input contract after requested changes (27 Nov); previous approval covered 21 inputs only.
- [x] Aminata confirms the worker's use of `POST /predict/batch`, retry/error policy, rejection, timeout and idempotency (technical COMMENT review, 27 Nov on the previous schema; not formal PR approval).
- [ ] The three reviewers agree on `POST /predict/batch` and the response `predictions`/`summary`, probability threshold, error semantics, queue poison strategy and exceptions.
- [ ] Update this document through a reviewed Pull Request before implementing incompatible changes.

**Related GitHub issues:** #2 #4 #5 #6 #7 #9 #10.


## 10. Integration decisions proposed for final R2/R1 review (24 Nov 2026)

These values reflect the current `feat/event-pipeline` implementation, not a new claim of team approval or deployed behavior.

- Worker HTTP connect timeout: **2 s**; read timeout: **10 s** (`API_CONNECT_TIMEOUT_SECONDS`, `API_READ_TIMEOUT_SECONDS`). These are separate limits, not a total wall-clock deadline. Confirm with R2 and test timeout/retry behavior.
- CSV: UTF-8 (BOM accepted), comma separator, canonical ordered header, no extra columns, blank rows ignored, decimal point, maximum 1 MiB and 10,000 rows. `customerID` required in CSV (1–64 ASCII characters matching `^[A-Za-z0-9._-]+$`, no surrounding whitespace); empty `TotalCharges` maps to null. Reject the entire file on any invalid nonblank row; no partial scoring. R2 must ensure permanent CSV errors in the worker are rejected rather than retried, including when content changes after dispatch.
- Rejection JSON currently implemented: `{"blobName":"batch_01.csv","reason":"validation error","status":"rejected"}`; reason limited to 2,000 characters. Confirm original-file retention and avoid sensitive values in logs.
- Cosmos ID currently implemented: sanitized filename stem (max 40 characters), hyphen, first 16 hex characters of SHA-256 of UTF-8 `blobName|etag`. Partition key `/fileName`. #21 implements conditional reads and version-specific canonical writes; 61 offline tests passed at 192e4c0. Concurrent duplicate deliveries can call inference twice; only durable output/metadata are deduplicated. Actual Azure adapters remain to be tested.
- R1/R4 selected the 19-feature model 1.1.0 with threshold 0.5. Recorded held-out AUC 0.8413 / F1 0.6136 / accuracy 0.7381, compared with historical 21-feature AUC 0.9273 / F1 0.7328. Keep dataset/artifact authorization explicit and re-run all affected tests.
- Integration: align the R4 branch with the current R1 API/ONNX/schema before sequential merging. Re-run the current-head integration gate. The infrastructure-only #24 can be reviewed and merged independently.
- R4: Omar confirmed `inferred_rows` for KQL; #19 dashboard consumes `{count,limit,results}` from `/api/recent`. Real Azure evidence remains pending.


## 11. Integration evidence and infrastructure proposals — 26 November

- #21 (192e4c0): 61 offline tests green, conditional ETag download, superseded event handling, immutable versioned output and Cosmos point reads on /fileName. Queue payload uses Base64 to match default Functions binding. Runtime adapters do not create cloud resources. Confirm these changes in review before freezing the interface.
- #22 (aea068a): 2 real ONNX offline integration tests green against API #17 and pipeline #21 pinned commits. No Azure service or training dataset download was involved.
- #23: integrated CI/GHCR/CD prepared with opt-in dataset/publication and deployment gates. #24: Bicep templates for Storage, Cosmos Free Tier (not serverless), Functions Flex, Container Apps, UAMI/RBAC/OIDC, monitoring. No Azure deployment executed. Align R4 resource names in #20 with the selected R3 configuration; no duplicate workspace.
- #18 remains gated on actual dataset/artifact permissions; revalidate #21/#22 with 1.1.0 before release. No claim of production validity.
- Pending R2 review: versioned output naming, superseded events, queue encoding, rejection overwrite policy, actual SDK/Functions binding behavior and real cloud test. Do not treat successful offline CI as deployment evidence.

### Historical review R1 follow-up — 26 November (1.0.0; superseded by 27 Nov migration)
Elias confirmed the working 21-feature interface, without freezing the 19/21 decision or approving the data rights. R2 aligned `customerID` validation on the API regex in #21 (503280a): 70 pytest cases and Ruff passed in run 45882123936. R1 API at 5886584: 15 tests, Ruff, Docker build and the <500 MB gate passed in run 45883545674; `publish-api.yml` is now manual, opt-in and limited to `preview-<commit-sha>`, with no new publication. R1 training at 3cb9ffe: 8 tests and Ruff passed in run 45881717150, with reproducible ablation. R1 telemetry implementation from #20 is now present on #17; #20 still needs review/rebase and remaining R4 configuration. QA approved the offline #22 preview at 65c11e9 (2 real ONNX + 3 isolated Azurite tests, run 45884397529); Azure scenarios E01–E11 remain unexecuted. The historical GHCR branch publication run 45880950088 succeeded for SHA 6fb916d, not the current integrated release, and is not an authorisation to distribute or deploy. Publication permission and final schema remain explicit decisions; no Azure deployment.

## 12. Naming and status conventions — coordination review 27 November

The following inventory matches the #24 Bicep defaults and the observed Work evidence; it is a proposal for the coordinator's explicit confirmation, not approval of deployment or a claim that the listed planned services exist.

| Item | Name / convention |
|---|---|
| Project group (reported created) | `rg-projet-g2cc` |
| Region | `francecentral` |
| GitHub identity / federation (reported created) | `dscc-github-mi` / `github-production` |
| Planned runtime identity | `dscc-runtime-mi` |
| Planned Storage / Cosmos accounts (availability previously checked) | `dsccg2cc20261126` / `dscc-g2cc-20261126` |
| Blob containers | `input`, `output`, `rejected`, `models`, `deployment`; static site `$web` after configuration |
| Queues | `inference-requests`, `inference-requests-poison` |
| Cosmos database / container / partition | `pipeline` / `inferences` / `/fileName` |
| Planned Container Apps environment / API | `dscc-env` / `dscc-api` |
| Planned Flex plan | `dscc-flex`; globally unique Function App name still to confirm |
| Monitoring | `dscc-logs`, `dscc-insights` |
| Output / rejection | `output/<blobName>.<idempotencyKey>.json`, `rejected/<blobName>.reason.json` |
| Status | `queued`, `ok`, `duplicate`, `rejected`, `superseded` as applicable to processing; retryable errors escape the worker |

No new resource is provisioned by this contract. The 19-feature integration target is based on the R1/R4 decision; the coordinator's acceptance, the full release gate, data rights and cloud evidence are distinct.
