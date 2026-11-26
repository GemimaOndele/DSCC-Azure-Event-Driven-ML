# DSCC — Azure Event-Driven Machine Learning

**ECE Paris · MSc 2 Artificial Intelligence · 2026–2027**  
**Course:** Distributed Systems and Cloud Computing in AI  
**Instructor:** Dr. BENNAI Soufia  
**Team:** Gémima ONDELE POUROU · Yaye Aminata DIAGNE · Elias CREMNITER · Omar KRARTI  
**Defense:** 2 December 2026

## Project goal

Build an event-driven Telecom Customer Churn prediction pipeline on Microsoft Azure, with file validation, queue-based decoupling, a containerized Machine Learning inference API, persisted results, a dashboard, observability, CI/CD, managed identities and a budget cap.

**Status (26 Nov 2026):** API, training, pipeline, dashboard, observability, CI/CD and infrastructure are in open PRs. Offline CI evidence exists; live Azure deployment and integrated release are not yet verified.

## Target architecture

```text
Client CSV → Blob Storage (input/)
                 ↓ BlobCreated
             Event Grid
                 ↓
      Azure Function dispatcher
        ├── invalid → rejected/
        └── valid   → Storage Queue inference-requests
                              ↓
                       Azure Function worker
                              ↓ POST /predict/batch
                    FastAPI + ONNX Runtime (proposed model)
                    Azure Container Apps
                              ↓
                output/ Blob + Cosmos DB
                              ↓
            HTTP Function GET /api/recent
                              ↓
                 Static website + Chart.js
```

Cross-cutting: Application Insights and OpenTelemetry, KQL and alerting, GitHub Actions CI/CD, OIDC, RBAC, budget controls and resource cleanup.

## Development scope and constraints

- Open dataset, at most **50 MB**; cite license.
- Reproducible CPU-based training, two metrics and a naive baseline; versioned model smaller than **100 MB**, inference below **1 s**.
- FastAPI (Python 3.12) endpoints `/health`, `/version`, `/predict`, `/predict/batch`, `/metrics`; Pydantic validation, three pytest cases and Docker image under **500 MB**.
- Python 3.12 Azure Functions app with dispatcher, worker, `recent`; five maximum queue deliveries and a poison queue, idempotency on Blob name + ETag.
- Azure budget **≤ $25** on one student's integration subscription; aim under **$5**.
- **No virtual machine, GPU or AKS. No secrets in this repository.**

## Current project organization

- [Start here — team branch assignments](TEAM-START-HERE.md) — first missions, branches and Git commands for all four students.

- [GitHub Project board](https://github.com/users/GemimaOndele/projects/5) — status, assignments, priorities and due dates.
- [Issue backlog](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues) — 12 top-level technical and delivery tasks.
- [Team roadmap and dependency plan](project-board-configuration.md).
- [Shared technical contract — draft](technical-contract.md) — subject to review by Gémima, Aminata and Elias.
- [Contribution guide](../CONTRIBUTING.md).

Work in feature branches and submit Pull Requests; `main` has an active ruleset requiring one approval and blocking deletion/force pushes.

## Planned repository structure

```text
model/             Training, evaluation, versioned model
api/               FastAPI, tests, Dockerfile
functions/         dispatcher, worker, recent, host.json
web/               HTML/JavaScript + Chart.js dashboard
infra/             Deployment scripts / Azure resources
.github/workflows/ CI and OIDC deployment workflows
docs/              Contracts, architecture, evidence, cost/time log
```

These folders will be added when the corresponding work begins, rather than populated with unfinished placeholders.

## Shared Azure collaboration

Gémima confirms that both she and Aminata have sufficient Azure for Students credits. Select **one** integration subscription after region and quota checks. The sharing/access guide was merged in PR #15; subscription and region selection remain pending. Other members may develop and test locally with Docker/Azurite/Azure Functions Core Tools. Azure deployment will use GitHub Actions OIDC; RBAC Contributor access to the resource group can be added only if the school's Microsoft Entra tenant allows it. **No paid Azure resource has been created by the GitHub setup work.**

## Deliverables

Public repository, README and reproducible code, a PDF report **with screenshots for each required step**, time log, actual-vs-estimated Azure cost report, oral defense and cleanup proof. The instructor stated that a demonstration video is **optional**, although the written specification mentions it.

## Evaluation focus

ML/API (4), event-driven pipeline (4), persistence/dashboard (2), observability (3), CI/CD/security (3), cost/student restrictions (2), documentation/demo/defense (2) = **20 points** (plus optional bonuses only after core completion).

_Last planning update: 26 November 2026. Consult the current PRs and evidence register before claiming acceptance. Dataset rights and final 19/21 decision remain pending._
