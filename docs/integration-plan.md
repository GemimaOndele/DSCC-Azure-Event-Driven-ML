# Integration and release sequence — proposed, 26 November 2026

No automatic merge is authorized. All branches remain separate; this plan is for
team review. Individual mergeability against main does not prove successive
merges are conflict-free.

## Historical overlap audit — 26 November (1.0.0)

Changed-filename intersections were checked across #14, #17–#25. These overlaps
are not all proven Git conflicts. Historical blob SHA prefixes:

| File | #14 | #17 | #18 | #20 |
|---|---|---|---|---|
| README.md | 3fd0410 | 6284711 | 2bbe20d | 6284711 |
| .gitignore | 7d0b789 | — | 8b5df60 | — |
| .github/workflows/ci-ml.yml | — | dde6dc3 | 3c5c41a | dde6dc3 |
| model/features.json | — | bf12ccd | b8b4eaa | bf12ccd |
| model/model-1.0.0.onnx | — | shared artifact per #17/#18 | shared | inherited #17 |

#20 includes inherited #17 files (API, Dockerfile, requirements, tests, model).
Its own observability changes should be reviewed against the final API after
#17 integration. #21–#25 currently have no changed-file intersections with the
other technical PRs; this is not a guarantee of runtime compatibility.

## Historical proposed sequence — superseded by infrastructure-first plan below
1. Confirm data/derivative rights and feature contract with Elias
   and the team. If model changes, synchronize ONNX, API schema, Functions
   contract and E2E fixtures before any integration. Obtain fresh reviews.
2. #14: agree version-specific output naming, superseded events, queue
   encoding, Cosmos /fileName, schema and telemetry. Gémima cannot approve it.
3. #17 then #18: proposed order, only after the above decisions. Rebase/update
   #18 on current main before review. Resolve README by retaining factual
   current routes/status; merge .gitignore as a union; preserve the approved
   single schema/model artifact. Reconcile ci-ml.yml; do not silently enable
   unauthorized dataset download. Run API/model tests and Docker again.
4. #20 after #17/#18: update onto current main, preserve observability changes
   and final API behavior; execute telemetry tests and Docker, no skipped CI
   presented as passed. Confirm privacy and R4 metrics.
5. #21: review the tested pipeline, update the schema copy to match the final
   model, rerun all pipeline tests and verify #14 contract. Keep evidence of
   ETag/duplicate handling and verify actual Azure adapters separately.
6. #19 after #21: correct dashboard validation, run tests and check the recent
   endpoint against final integrated output.
7. #22: rerun real ONNX integration against final assembled code rather than
   only the pinned preview; keep acceptance matrix. #23: review workflow lint,
   integrate after required modules and E2E test are on main, verify full CI.
   GHCR only after data rights and explicit opt-in.
8. #24 preflight is parallel documentation, not deployed infrastructure.
   Approve one subscription, region, quotas, budget, roles and GHCR pull setup.
   Complete #7 infrastructure with Aminata. Run manual deployment only when
   authorized; verify /version, Function App, event subscription and real E2E.
9. #25: finish report, costs, capture evidence and presentation after the tests.
   No fabricated costs or cloud results. Cleanup is separate post-defense work.

After each approved merge, update dependent branches before the next review,
check exact SHA and CI, and verify any stale approval. Only delete an integrated
branch after verifying its commits and no outstanding dependencies; no automatic
deletion is performed here. Keep main protected.

## Executed pairwise Git rehearsal — 26 November

GitHub Actions run 45883107858, job 140127055235, QA branch SHA 52103dd.
`git merge-tree --write-tree --name-only --no-messages` was run on 12 pinned pairs in a disposable runner. HEAD and working tree remained unchanged. No refs or PRs were merged. The JSON artifact records every exact input SHA. Outcome: five conflicting pairs and seven clean pairs.

| Pair | Result | Conflicting paths |
|---|---|---|
| #14 / #17 | conflict | README.md |
| #14 / #18 | conflict | .gitignore, README.md |
| #14 / #20 | conflict | README.md |
| #17 / #18 | conflict | README.md, model/features.json |
| #17 / #20 | clean | — |
| #18 / #20 | conflict | .github/workflows/ci-ml.yml, README.md, model/features.json |
| #17 / #21 | clean | — |
| #18 / #21 | clean | — |
| #19 / #21 | clean | — |
| #20 / #24 | clean | — |
| #23 / #24 | clean | — |
| #21 / #25 | clean | — |

Resolve README by retaining verified routes, new test evidence and final release status. Keep the union of ignore rules. Do not select feature schema or dataset metadata independently of the team's final decision. Preserve the final API/telemetry behavior and align the branch CI with #23. Rerun conflict rehearsal after head changes. Pairwise clean merges are not proof of sequential or runtime compatibility.

Run: https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45883107858

## Refreshed rehearsal and proposed resolution — 26 November

After moving the #14 overview to docs/project-overview.md and restoring its root README to main, pairwise conflicts dropped from five pairs to three, with nine clean pairs (run 45884397543, QA head 65c11e9). Remaining pairs: #14/#18 (.gitignore); #17/#18 (README.md, model/features.json); #18/#20 (ci-ml.yml, README.md, model/features.json). The latter does not conflict in the proposed sequence after #17.

Sequential preview run 45884397493 assembled all ten pinned PRs in a detached disposable worktree: #14 → #17 → #18 → #20 → #21 → #19 → #22 → #23 → #24 → #25. Only #18 needed resolution of .gitignore, README.md and model/features.json. For this preview, the #14 union of ignore rules, #17 API code/CI, #18 schema metadata (same 21 inputs), and proposed docs/release-readme.md were preserved. 15 API tests, 70 pipeline tests, 2 real ONNX integration tests, 16 dashboard tests and the R4 mocked CLI guards passed. Ruff passed; no training download or cloud operations. The exact pins and resolved paths are in the sequential-preview artifact. No remote PR merged. The schema choice is provisional, not team approval. For actual integration obtain independent review and resolve the remaining three files on the appropriate branch, rerun CI on each updated head, and re-check dataset/artifact authorization.

The #25 release gate later checked all C(10,2) = 45 pairs and the same ten-step sequence on synchronized heads without manual resolution. It also ran API, pipeline, E2E, dashboard and mocked R4 guards plus a local Docker build under 500 MB. Its pins were refreshed from the superseded #14/#25 commits to the reviewed heads; the PR head is injected into the gate so this self-referential check is not stale. This remains an offline rehearsal: no remote merge, GHCR push, Azure deployment, dataset download or acceptance scenario is performed.

## Current 27 November plan — 1.1.0 / infrastructure first

#24 at 78ac96d was independently approved for preflight/documentation by Elias; CI 45962535851 passed. The owner authorized its normal merge into protected main, completed at e56f77c. The infrastructure branch was absent after merge. READ-DSCC on main succeeded after correcting the existing federation and obtaining personal production approval (run 45966902708 attempt 2). #26 was independently approved by Omar and merged at c67bafc after CI 45970191053 passed, preserving the corrected subject in IaC. Next: refresh quota, costs and what-if. No model or dataset was needed for the read-only OIDC test. Refresh actual quota, Free Tier, RBAC and what-if before any provision. Do not conflate preflight with permission to deploy.

R1/R4 selected ONNX 1.1.0 / 19 features (blob 09ee933f); #17 and #18 synchronized their artifacts and schema. #20 65ff2d2 is stacked on #17 846a697, preserving R1 byte-for-byte; the delta is nine observability files (45964577085); #21 aligned its schema and 72 tests, #19 updated sample version with 17 tests, #22 passed 2 ONNX + 3 Azurite tests with 1.1.0. The new 1.1.0 release gate succeeded: 45 pairs and ten sequential merges, 107 tests, Ruff, mocked guards and Docker under 500 MB (45964613679, 45964640260); no remote merge. The dynamic run records exact heads, and subsequent documentation-only changes are separate. Remaining proposed order after #24 and #26: #14 → #17 → #18 → #20 → #21 → #19 → #22 → #23 → #25, subject to team review, rights clearance and current CI. Do not use the historical 21-feature reports as proof of the new release. No automatic merge.

### QA revalidation after the OIDC fix

#22 b5181e1 resolves Omar's stale-snapshot review: main c67bafc, 55 pairwise comparisons and nine pending integrations; reports are outside the checkout and conflicts fail closed. Runs 45981804434, 45981804366 and 45981804373 passed (107 integrated tests, separately 2 ONNX + 3 Azurite). The latest dashboard-only change ccb406c corrects the README example to 1.1.0; CI 45981945036 passed. The snapshot precedes this documentary change. The dynamic release gate attempt 3 of 45964640260 also passed (107 tests, image 100599122 bytes), but its original PR list predates #26. No cloud acceptance or model publication implied.
