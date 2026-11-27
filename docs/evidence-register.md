# Evidence register and team journal — issue #12

Do not enter invented hours or mark planned checks completed. Each member fills
their actual session dates, durations and links. Course target: 12 h/person.
The 26 November entry below records repository actions, not inferred personal hours.

| UTC date | Contributor / domain | Action | Evidence | Status |
|---|---|---|---|---|
| 24 Nov | Elias / R1 | API tests and build | PR #17, SHA 5388f1c | CI success |
| 24 Nov | Elias / R1 | Training tests | PR #18, SHA 5c7eb97 | CI success; data rights pending |
| 24 Nov | Gémima + Aminata | Azure access guide | PR #15, merge fae1d19 | Merged, not deployed |
| 26 Nov | Gémima / R2 | Pipeline hardening and test workflow | PR #21, SHA 192e4c0, Actions 45878414101 | 61 offline tests passed |
| 26 Nov | Gémima / QA, R3 | E2E preview, CI/CD and preflight preparation | Branches test/e2e-scenarios, ci/github-actions, infra/azure-core | Prepared; cloud not run |
| 26 Nov | Gémima / QA | Real ONNX offline integration preview | PR #22, Actions 45878841099 | 2 passed, 2 warnings; no cloud |
| TBD | All | Azure integration and acceptance | Issue #11 | Pending |
| TBD | All | Report, rehearsal, delivery | Issue #12 | Pending |

For each evidence file, record: date/time UTC; author; issue and PR; exact commit;
environment; expected/observed; test result; file/link; any incident; actual time spent.
Use synthetic customer IDs. Do not include subscription ID, access token, secret,
email, endpoint key or unredacted input/output data in public evidence.

| 26 Nov | Gémima / R3 | Azure Bicep templates and guarded bootstrap | PR #24, commit d62968f, Actions 45880668170 | Compilation and guard tests passed; not deployed |
| 26 Nov | Gémima / R3 | Align GHCR registry mode in CD | PR #23, commit 44881d2, Actions 45880607362 | Workflow lint passed; no release/deploy |

Credit sufficiency for both student subscriptions is confirmed by the coordinator from previously shared evidence; selected owner and live region/quotas still require confirmation.

### R1/R2 follow-up — 26 Nov

| Contributor | Proof | Result |
|---|---|---|
| Elias | #17 69cf39c, run 45881702134 | 15 tests + Ruff + Docker build |
| Elias | #18 3cb9ffe, run 45881717150 | 8 tests + Ruff; data rights pending |
| Elias | GHCR run 45880950088, SHA 6fb916d | Branch image published, digest recorded in report; final deployment pending |
| Gémima / R2 | #21 503280a, run 45882123936 | 70 tests + Ruff; customerID review addressed |
| Gémima / R3 | #23 d972d2d, run 45882157727 | Actionlint passed; integrated components absent on isolated branch; publication skipped |

| Gémima / QA | #22 886ee85, run 45882194925 | Refreshed real ONNX integration: 2 passed, 2 warnings; 11 Azure acceptance scenarios prepared |

| Gémima / QA | #22 1cccf50, run 45883033290 | 2 ONNX tests + 3 actual SDK tests with isolated Azurite, passed; first fixture attempt failed and was corrected |
| Gémima / integration | #22 52103dd, run 45883107858 | 12 pairwise Git rehearsals: 5 conflict, 7 clean; no remote merge |
| Gémima / CI | #23 783dac9, run 45882995776 | Actionlint passed; added API image size gate <500 MB and release digest evidence; component build/publish not executed on isolated branch |

### Integration hardening — 26 November

| Contributor | Proof | Result |
|---|---|---|
| Gémima / coordination | #14 8671309 | Move overview to docs; eliminate root README change |
| Elias / integration sync | #17 8672dfd, run 45885173139 | Shared README/features/CI synchronized without changing model code; 15 API tests, Ruff, Docker and <500 MB gate green; preview-only manual GHCR workflow retained; no new publication |
| Gémima / integration sync | #18 3b489d1, run 45885194571 | Shared README/features/.gitignore/CI synchronized; model and artifact unchanged; offline training tests green |
| Elias | #14 a281fb8 | R1 contract validation; repaired duplicated document and `customerID` regex; 19/21 and rights still pending |
| Elias | #22 65c11e9 review | Approved offline preview and acceptance plan; Azure E01–E11 remain unexecuted |
| Gémima / R4 support | #19 2f57b64, run 45884267755 | 16 Node tests passed |
| Gémima / R4 support | #20 b81277f, run 45884243968 | Mocked command guards, 15 API tests (overlap R1), Ruff and Docker passed |
| Gémima / QA | #22 65c11e9, run 45884397543 | 3 pairwise conflicts, 9 clean |
| Gémima / QA | #22 65c11e9, run 45884397493 | Sequential 10 PR preview, 103 tests passed, Ruff and guards passed |
| Gémima / QA | #22 65c11e9, run 45884397529 | 2 ONNX + 3 Azurite tests passed |
| Gémima / CI | #23 fdfc432, run 45884272396 | Integrated R4 jobs added; workflow CI success on isolated branch |
| Gémima / release gate | #25 offline gate | All 45 PR pairs and 10 sequential merges clean on synchronized heads; local Docker build <500 MB; pins refreshed for current #14/#25 heads; no publication or deployment |

No remote merge, real Azure resource operation or publication was performed by the coordinator. Remaining dataset/artifact permission, schema decision, human reviews and live cloud validation are explicit release gates.

## 27 November — 19-feature / ONNX 1.1.0 migration

| Scope | Commit and run | Verified result |
|---|---|---|
| R1 API | #17 846a697; 45961769605 | 16 pytest, Ruff, Docker green |
| R1 training | #18 e7d8272; 45961524670 | 4 offline checks, Ruff, 4 dataset-dependent tests deselected; reported 1.1.0 metrics AUC 0.8413 / F1 0.6136 / accuracy 0.7381 |
| R2 | #21 d4e5138; 45962557654 | 72 pytest + Ruff; retired ticket columns rejected |
| R4 dashboard | #19 c852877; 45963960460 | 17 Node tests, returned version preserved |
| R4 monitoring | #20 65ff2d2; 45964577085 | Independent mocked CLI/curl guards; R1 dependency exact and nine-file R4 delta |
| QA | #22 8f41a99; 45963915557 | 2 real ONNX + 3 Azurite SDK tests, 19-feature schema and blob verified |
| R3 | #24 78ac96d; 45962535851 | CI green, Elias APPROVED preflight/docs only; no OIDC execution or deployment |

Prior 1.0.0 runs above are historical. The 1.1.0 integrated gate is verified by 45964613679 and 45964640260: 45 pairs clean, ten sequential merges clean, 16 API + 72 pipeline + 2 ONNX + 17 Node = 107 tests, Ruff, mocked guards and Docker ~100.6 MB. The tested #25 script was 6a5cabe and the dynamic #23 head was 478bc82; later report-only changes are not covered by the exact earlier snapshots. Azure acceptance remains separate. No new dataset download, publication or remote merge by the coordinator. Work evidence records initial resource group, budget and OIDC identity configuration; actual deployment, cost and quota evidence pending.

### Infrastructure integration milestone — 27 November

| Event | Evidence | Status |
|---|---|---|
| #24 independent review and merge | Elias APPROVED 78ac96d; CI 45962535851; merge e56f77c | Merged into protected main (one independent approval required; no bypass). |
| Read-only workflow | `.github/workflows/azure-oidc-readonly.yml` on main, blob 54c9a2ad | Present; no real OIDC execution observed at verification. |
| Branch inventory | `infra/azure-core` absent after merge | No manual branch deletion performed in Chat. |

All application provisioning, actual quota and Free Tier checks, owner approval of production, dataset/artifact authorization and cloud acceptance remain open. No deployment enabled or Azure charge incurred by this merge.

### Live OIDC recovery — 27 November 2026

| Event | Evidence | Result |
|---|---|---|
| First attempt | Run 45966902708 attempt 1 | AADSTS700213, legacy subject mismatch |
| Corrected existing credential | Work account of 27 Nov | Subject updated in place; no additional identity reported |
| Actual OIDC verification | [Attempt 2](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45966902708/attempts/2), job 140414854878 | SUCCESS: Azure login, expected subscription, RG France Central, logout; independently verified in logs |
| IaC correction | #26 a3f5b233, run 45970191053 | Immutable subject/issuer/audience assertions passed; Omar approved a3f5b233 and #26 merged at c67bafc |
| Cosmos Free Tier | Work account | Option selectable; no account created, effective Free Tier unverified |

No application resources deployed. The local Work archive and twelve captures are reported saved by Work; their bytes were not independently inspected in Chat. Refresh quota/cost checks and what-if now that #26 is integrated.

### Post-fix QA and review checkpoint — 27 November

| Scope | Evidence | Result |
|---|---|---|
| #26 | a3f5b233, 45970191053, merge c67bafc | Omar APPROVED; IaC subject matches working federation |
| #22 | b5181e1, 45981804434 | 55/55 pairs clean on explicit snapshot |
| #22 | b5181e1, 45981804366 | Nine pending PR integrations clean; 107 tests, Ruff and mocked guards |
| #22 | b5181e1, 45981804373 | 2 real ONNX + 3 Azurite tests |
| #23 | 45964640260 attempt 3 | Dynamic gate passed, 107 tests, image 100599122 bytes; original PR set excludes #26 |
| #19 | ccb406c, 45981945036 | README-only correction, dashboard CI passed |
| R4 review | Omar, 27 Nov 10:15 UTC | Approved current #14/#17/#18/#21/#23; #18 rights remain unresolved; #22 requires re-review |

Omar reports eight local training tests for 1.1.0; the actual current training CI remains four offline tests passed and four dataset-dependent tests deselected. Do not equate reported local results with a CI download authorization. Azure application infrastructure and E01–E11 remain pending.

### Integration into protected main — 27 November 11:23–11:24 UTC

| Event | Evidence | Result |
|---|---|---|
| #14 contract merged | merge 3e298c1, Elias APPROVED after 19-feature corrections, Omar APPROVED | Merged into main; shared schema now 1.1.0 / 19 inputs |
| #17 API merged | merge 1357387, checks 45961769605 | Merged; 16 API tests, Ruff, Docker and <500 MB gate green |
| #21 pipeline merged | merge 0f2d4f2, checks 45962557654 | Merged; 72 offline tests and Ruff green |
| #23 CI/CD merged | merge b519575, checks 45964640245 / 45964640260 | Merged; workflow lint, integration gate and infrastructure-first green |
| #18 training | head e7d8272, Omar APPROVED; Gémima re-review requested 7217023572 | Not merged until the historical change request is resolved |
| #20 monitoring | branch pushed to 900c728, R4-only nine-file delta over current main | Re-review pending; cloud alert still unexecuted |
| #19 dashboard / #22 QA | renewed reviews requested on ccb406c and b5181e1 | No cloud acceptance claimed |
| #25 report | this update | Draft until rights, captures, costs and cloud evidence are complete |

No GHCR release, deployment flag activation, dataset download, Azure resource creation or cost was incurred by these merges.
