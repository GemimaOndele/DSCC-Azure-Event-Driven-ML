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
| Elias | #17 5886584, runs 45883545674 and 45883553318 | 15 API tests, Ruff, Docker and <500 MB gate green; preview-only manual GHCR workflow; no new publication |
| Elias | #14 a281fb8 | R1 contract validation; repaired duplicated document and `customerID` regex; 19/21 and rights still pending |
| Elias | #22 65c11e9 review | Approved offline preview and acceptance plan; Azure E01–E11 remain unexecuted |
| Gémima / R4 support | #19 2f57b64, run 45884267755 | 16 Node tests passed |
| Gémima / R4 support | #20 b81277f, run 45884243968 | Mocked command guards, 15 API tests (overlap R1), Ruff and Docker passed |
| Gémima / QA | #22 65c11e9, run 45884397543 | 3 pairwise conflicts, 9 clean |
| Gémima / QA | #22 65c11e9, run 45884397493 | Sequential 10 PR preview, 103 tests passed, Ruff and guards passed |
| Gémima / QA | #22 65c11e9, run 45884397529 | 2 ONNX + 3 Azurite tests passed |
| Gémima / CI | #23 fdfc432, run 45884272396 | Integrated R4 jobs added; workflow CI success on isolated branch |

No remote merge, real Azure resource operation or publication was performed by the coordinator. Remaining dataset/artifact permission, schema decision, human reviews and live cloud validation are explicit release gates.
