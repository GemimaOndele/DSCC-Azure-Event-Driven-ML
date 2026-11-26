# Integration and release sequence — proposed, 26 November 2026

No automatic merge is authorized. All branches remain separate; this plan is for
team review. Individual mergeability against main does not prove successive
merges are conflict-free.

## Verified overlap audit

Changed-filename intersections were checked across #14, #17–#25. These overlaps
are not all proven Git conflicts. Current blob SHA prefixes:

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

## Proposed sequence
1. Confirm data/derivative rights and final 19/21 feature decision with Elias
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
