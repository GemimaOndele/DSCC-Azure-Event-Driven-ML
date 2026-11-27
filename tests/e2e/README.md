# DSCC acceptance test plan — issue #11

Status: prepared, not executed on Azure. Offline pipeline CI has 72 passing tests on d4e5138 (1.1.0, 19 inputs); this is not cloud acceptance.

## Local integration (after #17, #18, #21 are merged)
From the repository root in Python 3.12:
```bash
python -m pip install -r api/requirements-dev.txt -r functions/requirements.txt
python -m pytest tests/e2e/test_pipeline.py -q --junitxml=e2e-local.xml
```
This uses the real ONNX API in process, in-memory storage and queue, and synthetic rows
generated from the feature contract. It does not download the training dataset or
create cloud resources. Run only after the agreed model/contract is integrated.
It is not a test of Event Grid, Functions triggers, Azure Storage or Cosmos.

## Azure acceptance matrix (manual after #7/#8 and budget approval)

| ID | Scenario and procedure | Expected | Evidence | Owner |
|---|---|---|---|---|
| E01 | Upload unique synthetic CSV into input/ and record UTC | Dispatcher queues, Worker calls batch API, versioned output + one Cosmos record within 60 s | Input/queue/output/Cosmos timestamps and latency | Gémima + Aminata |
| E02 | Upload invalid CSV header / invalid cell | Rejected reason, no scoring, no sensitive row values | Rejected JSON + logs, redact names | Gémima |
| E03 | Use an agreed isolated fault-injection setup for transient HTTP 503; restore config after test | Five deliveries then poison queue; no success row | Host logs with dequeue count and poison queue | Aminata + Gémima |
| E04 | Replay exactly the same message and ETag, then replay concurrently | One canonical result and one metadata item; concurrent API calls can occur | Blob count, Cosmos ID, logs | Gémima |
| E05 | Replace same blob with a new ETag after first success; send old event | Old output preserved; old input not re-scored as new bytes | Two distinct output keys, superseded status | Gémima + Aminata |
| E06 | Open dashboard and upload another valid batch | New result within refresh interval after persistence; correct KPIs | Timestamped screen and API JSON | Omar |
| E07 | Run approved manual deployment and compare /version | API release ID equals deployed commit; Functions present | Actions run, version JSON | Gémima + Aminata |
| E08 | Observe Container Apps after idle period | 0 replicas if configuration permits | Azure Metrics/replicas evidence, time window | Aminata |
| E09 | Trigger agreed R4 alert with safe synthetic requests | KQL metrics, alert fired and email | KQL query results and alert history | Omar |
| E10 | Read Cost Analysis and check RBAC and secrets | Within approved budget; least privilege; no committed credentials | Redacted Cost Analysis and role assignments | All |
| E11 | Compare approved GHCR digest and SHA tag to Container Apps revision and GET /version | Deployed image digest and release ID match the approved release commit | GHCR push logs, revision metadata, version JSON | Gémima + Elias |

## Evidence register
For each run, record date/time UTC, environment (offline / Azure), exact commit,
input fixture ID, test ID, expected, observed, pass/fail, evidence filename and owner.
Do not mark an acceptance test passed without an observed result.
Keep raw customer records, connection strings, URLs with keys, personal emails and
tokens out of screenshots and logs. Use synthetic input names and IDs.

## Release gate
Dataset rights and feature contract confirmed; CI passed on integrated main; GHCR
image digest known; region/quotas/budget approved; Azure deployment explicitly
authorized. No automatic provisioning or fault injection into a shared environment.
After demonstration, cleanup is a separate authorized operation and must be evidenced.

R1 branch GHCR publication observed in run 45880950088: tag 1.0.0 and sha-6fb916d19230cdd29fccffccdf3722704f1f8b25, digest sha256:7932660bde49aeeaffad67fd58f5609a80ab123b11b632d663a0f88adab3b3f8. This proves branch publication, not integrated main, model publication authorization or Azure deployment. E11 remains unexecuted.

## Current offline rehearsal snapshot — 27 November

The two rehearsal scripts pin main c67bafc (merged #24 and #26) and the nine remaining PRs; CI injects the actual QA PR head. Refresh the explicit snapshot after any other PR advances; the dynamic #23 gate is an additional current-head check. Both fail on any conflict, and store evidence outside the checkout (DSCC_REPORT_DIR or a temporary directory). For local runs use the QA head and full Git history, and set PR22_HEAD to that exact SHA. The sequential check validates the matching schema, actual 1.1.0 ONNX blob and offline integration tests; the pairwise check covers all 55 pairs. No cloud acceptance test has run.
