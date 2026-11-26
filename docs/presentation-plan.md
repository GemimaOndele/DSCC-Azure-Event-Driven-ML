# Defense preparation — 2 December 2026
**10-minute presentation + 5-minute Q&A (issue #12).** Proposed speaking order;
team approval pending. No claim of a completed Azure demo before evidence.

| Time | Slide / speaker | Key message / evidence |
|---|---|---|
| 0:00–0:40 | 1. Problem and goals — Gémima | Telecom attrition, event-driven batch scoring |
| 0:40–1:40 | 2. Architecture — Gémima | Blob → Event Grid → queue → worker → ONNX → output/Cosmos → dashboard |
| 1:40–3:10 | 3. Model & API — Elias | Feature decision, rights, model metrics and /predict/batch, CI |
| 3:10–4:40 | 4. Pipeline — Gémima | ETag, idempotent output, retries, rejection, 61 offline tests + 2 real ONNX preview tests |
| 4:40–6:10 | 5. Azure and CI/CD — Aminata | Subscription, resource design, OIDC, GHCR digest, approved deployment |
| 6:10–7:40 | 6. Monitoring & dashboard — Omar | Dashboard refresh, KQL metrics, email alert, actual cost |
| 7:40–9:15 | 7. Demonstration / acceptance — team | Synthetic CSV, result, dashboard, telemetry, version; evidence only |
| 9:15–10:00 | 8. Conclusions — Gémima | Acceptance summary, limitations, cost/cleanup plan |

## Suggested opening (English)
Our project is an event-driven machine learning pipeline for telecom customer
attrition. Instead of running an always-on server or manually triggering every
prediction, we process uploaded CSV batches through Azure storage events, queue
workers and an ONNX inference API. Our design focuses on reliability, cost control
and reproducibility, with explicit validation and traceable CI evidence.

## Demonstration checklist
- Before presenting: verify approved subscription, current deployed commit,
  /health and /version; open dashboard, Blob Storage, Cosmos/approved fallback,
  and Application Insights. Use a unique synthetic filename.
- Upload CSV; record UTC. Observe output and metadata, show the dashboard refresh.
- Show a pre-recorded invalid CSV rejection, bounded retry/poison result, KQL and
  alert evidence rather than consuming presentation time on asynchronous waits.
- Show CI run, image digest, actual Cost Analysis and limits; redact identifiers.
- If Azure unavailable: demonstrate offline real-ONNX pipeline (verified preview run 45878841099) and clearly label
  cloud acceptance incomplete. Never use mock results as Azure proof.
- Final slide: confirmed vs pending, limitations, cleanup after separate approval.

## Q&A preparation
- Why queue decoupling? Backpressure, independent scaling and bounded retry.
- Exactly once? No. At-least-once delivery; one immutable persisted result per
  blobName+ETag, possible duplicate API calls during races.
- Why ETag? Prevent scoring new bytes against an old event version.
- What is poison queue? After five failed deliveries the host moves the message;
  a real Azure-host test is needed.
- Why ONNX? Portable model inference; reproducible model/interface versioning.
- Why 19 vs 21? Ticket variables may not be available at prediction time; team
  decision and dataset authorization are prerequisites.
- Why Cosmos partition /fileName? Point reads must match the configured partition.
- Why OIDC? Short-lived ARM tokens without persistent Azure client secret.
- How to control cost? Budget alerts, consumption plans, capped log ingestion,
  scale-to-zero and post-defense authorized cleanup; budget is not a hard cap.
- What has actually been proved? Cite CI and real acceptance evidence, not planned tasks.

## Rehearsal
Each person prepares the slide content and can explain one neighboring component.
Run a timed 10-minute rehearsal; record actual evidence links and unresolved issues.
