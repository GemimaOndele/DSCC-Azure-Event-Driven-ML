# Contributing to DSCC Azure Event-Driven ML

This is a four-person ECE Paris academic project with a defense scheduled for 2 December 2026.

## Team workflow

1. Take an assigned Issue from [GitHub Projects](https://github.com/users/GemimaOndele/projects/5). Check its dependencies, priority and deadline.
2. Work in a **feature branch**, never directly in protected `main`.
3. Write or update tests; keep a screenshot or a reproducible command for each graded requirement.
4. Create a Pull Request to `main`, reference its Issue and explain what changed and what was tested.
5. Receive **at least one approval** and only then merge. GitHub ruleset `DSCC — Protection main` enforces this rule.
6. Move the Issue to **In Review**, and finally **Done** only when validation and evidence are complete.

## Branches

- `docs/azure-sharing` — Aminata, Azure access documentation first.
- `feat/ml-training`, `feat/ml-api` — Elias, model and API.
- `feat/event-pipeline`, `infra/azure-core` — Aminata + Gémima, Functions and integration subscription.
- `feat/dashboard`, `feat/observability` — Gémima as temporary relay, Omar when available.
- `docs/project-management` — coordination documentation (initial PR merged).
- `docs/technical-contract` — shared contract draft for review.

## Security and budget

**Never commit** `.env`, `local.settings.json`, Azure tokens, passwords, keys or connection strings. Use identity-based access and GitHub Actions OIDC. No Azure resources should be provisioned without confirming the selected subscription, permitted region, quotas and the USD 25 ceiling.

## Roles and availability

- Gémima: project coordination, GitHub, technical contract, CI/CD and Azure integration.
- Aminata: Azure sharing documentation, then infrastructure and pipeline with Gémima.
- Elias: data preparation, model, FastAPI and tests, all initially local.
- Omar: dashboard/KQL/tests when available. His temporary unavailability must not block the critical path.

## Pull Request template

Describe:
- Related Issue and dependencies
- Scope of change
- Tests executed and outcomes
- Screenshots/evidence (redact secrets)
- Azure resources and cost impact (if any)
- Any change to technical contract or architecture

See [team roadmap](docs/project-board-configuration.md). Work logs, decisions, screenshots and restrictions are collected in the shared Word and the final report.
