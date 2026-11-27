# Deployment runbook — DSCC Azure, 26 November 2026

**Credit sufficiency is confirmed by the coordinator for Gémima and Aminata.**
Do not request the historical screenshots again. One of the two subscriptions is
selected for the actual project; the other is a contingency, not a second
environment. The selected owner controls the Azure login and spending.

Status: scripts/templates in review, no Azure deployment executed. This guide is
a controlled runbook, not permission to spend. The target RG name
`rg-projet-g2cc` and region `francecentral` come from #15; only use the region
after the selected subscription permits it.

## Stage 0 — owner session, collaboration and budget
1. The chosen owner opens their own Azure Portal / Cloud Shell. Use
   `az account show --query "{name:name,state:state}" -o table`. No shared login,
   session cookies, passwords or tokens. Run `bash infra/preflight-readonly.sh`
   to inspect regions/provider availability. Check actual regional quotas,
   Cosmos Free Tier eligibility and remaining active credit in the selected account.
2. Owner creates the single tagged RG only after approval of the budget and
   region. Set project budget ≤ USD 25 (internal target < USD 5), with alerts at
   20%, 50%, 80% in Cost Management. If student subscription cannot create a
   budget, stop and agree an alternative documented cost-control mechanism with
   the teacher; don't pretend budget alerts enforce a cap.
3. Invite the other R3 member through Entra B2B if tenants differ. Use their
   **guest object ID in the owner's tenant**, not their home-tenant ID. Grant
   Contributor to the RG only; the owner handles role assignments. Use the
   already merged docs/azure-access-guide.md and the commands below.

```bash
# Owner only, after group and access scope are approved. Replace local placeholders.
RG=rg-projet-g2cc
RG_ID="$(az group show -n "$RG" --query id -o tsv)"
az role assignment create --assignee-object-id "$R3_GUEST_OBJECT_ID" \
  --assignee-principal-type User --role Contributor --scope "$RG_ID"
# Optional, separate approval for Omar: read-only monitoring, not Owner/Contributor.
az role assignment create --assignee-object-id "$R4_GUEST_OBJECT_ID" \
  --assignee-principal-type User --role "Monitoring Reader" --scope "$RG_ID"
```

Elias can continue offline, and gets only explicitly required access. For the
demo, Omar may also need Log Analytics Reader on the specific workspace; grant
only after reviewing telemetry data sensitivity. Storage Blob Data Contributor
for a test operator should be scoped to the input container, not the subscription.
RBAC propagation may take time. If Entra B2B is blocked, the owner shares their
screen and executes commands while other members guide the session; nobody
shares account credentials.

## Stage 1 — base infrastructure, independent of final model
Use the existing branch and review PR #24. Once approved, the owner can prepare
the base resources in parallel with ML reviews. For reproducibility run from the
reviewed repository checkout, with a current Azure CLI/Bicep installed. The RG
must already exist with the budget controls in place.

```bash
# LOCAL values, never commit this environment.
export DSCC_SUBSCRIPTION="$(az account show --query id -o tsv)"
export DSCC_RG=rg-projet-g2cc
export DSCC_REGION=YOUR_VERIFIED_REGION
export DSCC_STORAGE=YOUR_UNIQUE_LOWERCASE_STORAGE_NAME
export DSCC_COSMOS=YOUR_UNIQUE_COSMOS_NAME
export DSCC_BACKEND=cosmosFreeTier
export DSCC_PREFIX=dscc
bash infra/bootstrap.sh plan-base
```

Inspect what-if and stop on unexpected resources or a missing provider.
After human approval of the exact plan, budget and free-tier eligibility:

```bash
export DSCC_APPROVAL=APPROVED-DSCC-BUDGET-25
bash infra/bootstrap.sh apply-base
unset DSCC_APPROVAL
```

Base contains LRS Storage, private containers and queues, runtime UAMI,
GitHub UAMI with production-environment federation, scoped RBAC, monitoring,
Cosmos Free Tier with 400 RU/s shared throughput and /fileName partition.
Cosmos Free Tier is not serverless; it must be eligible and enabled at account
creation. If Cosmos creation fails, review any partially created resources and
costs. Do not retry with paid Cosmos or silently switch backend. Explicitly
approve the Table fallback and update the team contract before running a new
plan. The what-if is not a cost estimate or guarantee of capacity.

Do not store identity IDs or deployment output in public evidence. The owner
uses the output client/tenant/subscription IDs to configure GitHub environment
variables AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID. Set required
reviewers if supported, environment production restricted to protected main.
Keep AZURE_DEPLOY_ENABLED=false until the release is approved.

## Stage 2 — application infrastructure (after approved model/image)
The delivered R1 model is `1.1.0` with 19 inputs: `numAdminTickets` and
`numTechTickets` were removed because their availability before `Churn` is not
documented. Confirm the approved image reports `model_version=1.1.0` at `/version`
and that its ONNX blob matches the one shared by #17/#18. After approved integration and successful CI on main,
set MODEL_ARTIFACT_PUBLISH_APPROVED and ENABLE_GHCR only with documented rights to publish
the artifact. DATASET_USE_APPROVED independently gates training/download. The R1 branch image published on 26 November (run 45880950088, SHA 6fb916d) was built with the retired 21-feature `1.0.0` model: it is evidence of branch publication only, not final release or permission; do not deploy it. Publish immutable SHA-tagged image, record digest. Private GHCR
requires a separately authorized scoped read token stored as an Azure secret.
The bootstrap prompts for this only in the owner's terminal, never via chat.
Public registry option requires explicit package visibility approval.

```bash
export DSCC_FUNCTION=YOUR_UNIQUE_FUNCTION_APP_NAME
export DSCC_IMAGE=ghcr.io/gemimaondele/dscc-azure-event-driven-ml/churn-api@sha256:YOUR_VERIFIED_DIGEST
export DSCC_REGISTRY_MODE=private
export DSCC_COSMOS_ENDPOINT="$(az deployment group show -g "$DSCC_RG" -n dscc-base --query properties.outputs.cosmosEndpoint.value -o tsv)"
export DSCC_DASHBOARD_ORIGIN=""
export DSCC_EXPOSURE_APPROVAL=approved-synthetic-demo
bash infra/bootstrap.sh plan-apps
# Only after approval of the plan and public-demo exposure:
export DSCC_APPROVAL=APPROVED-DSCC-BUDGET-25
bash infra/bootstrap.sh apply-apps
unset DSCC_APPROVAL
```

The current API and recent endpoint lack application-level authentication.
External ingress is therefore an explicit temporary academic demo option, with
synthetic inputs/filenames only and a short monitored demonstration window.
CORS is not authentication. Public endpoints can be abused and incur costs.
For real customer data or longer operation, implement authenticated ingress
or private networking first; do not enable public access for that use.
Verify 0.25 vCPU/0.5 GiB is sufficient for ONNX; no always-on replicas.
Flex Functions uses a separate package deployment container and UAMI.

## Stage 3 — dashboard, application release and Event Grid
- Once authorized, enable the static website on project storage using the
  owner's approved data-plane permissions. For example:
  `az storage blob service-properties update --account-name "$DSCC_STORAGE" --auth-mode login --static-website true --index-document index.html`.
  Obtain the exact origin from the storage primary web endpoint (remove trailing
  slash); publish only the reviewed static web files, no customer data or secrets.
  Set DASHBOARD_ORIGIN on the Function App to this exact origin. Dashboard
  config.js contains only the approved Function App base URL. Do not add a
  duplicate platform CORS header.
- GitHub production variables: AZURE_RESOURCE_GROUP, AZURE_CONTAINER_APP,
  AZURE_FUNCTION_APP, GHCR_REGISTRY_MODE, AZURE_CLIENT_ID, AZURE_TENANT_ID,
  AZURE_SUBSCRIPTION_ID. Enable AZURE_DEPLOY_ENABLED only after owner approval.
  Launch deploy.yml manually on main with confirmation DEPLOY-DSCC.
  Verify /health and /version (commit-specific API release), and dispatcher,
  worker and recent are listed. No Azure resource deployment in CI itself.
- Connect Event Grid only after dispatcher exists:
```bash
export DSCC_APPROVAL=APPROVED-DSCC-BUDGET-25
bash infra/bootstrap.sh connect-event-grid
unset DSCC_APPROVAL
```
  Endpoint uses Azure Function resource ID, not a shared webhook key; filter
  BlobCreated and input container .csv subjects.
- Execute the ten acceptance scenarios in tests/e2e/README.md. Start with one
  small synthetic CSV, review actual spend and telemetry before further traffic.
- Apply reviewed R4 alert configuration (#20) to the same existing workspace
  and Application Insights; do not duplicate resources or create a second
  monitoring workspace. Confirm exact names and CLI behavior first.
- Record Cost Analysis, logs, status and actual resource inventory. Cleanup
  after defense is a separate approved action. Disable deployment flag when done.

## Sources
- Azure Functions Flex IaC: https://learn.microsoft.com/en-us/azure/azure-functions/functions-infrastructure-as-code
- Flex CLI and deployment: https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to
- Identity-based connections: https://learn.microsoft.com/en-us/azure/azure-functions/manage-connections
- Cosmos Free Tier: https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier
- Cosmos data roles: https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/how-to-connect-role-based-access-control
- Event Grid trigger: https://learn.microsoft.com/en-us/azure/azure-functions/event-grid-how-tos

## OIDC incident recovery (27 November 2026)

The first manually approved read-only run 45966902708 failed before resource enumeration with AADSTS700213. GitHub now emits the immutable subject (owner and repository IDs). `infra/base.bicep` must match that exact subject. The existing `github-production` credential on `dscc-github-mi` must be updated in place by the authorized owner, after checking the selected subscription and existing issuer/audience. Use Azure CLI `az identity federated-credential update --resource-group rg-projet-g2cc --identity-name dscc-github-mi --name github-production --issuer https://token.actions.githubusercontent.com --subject 'repo:GemimaOndele@128593071/DSCC-Azure-Event-Driven-ML@1462622773:environment:production' --audiences api://AzureADTokenExchange`. Verify with `show` and rerun READ-DSCC on main with the normal production approval. Do not change the GitHub subject template, grant broader access, duplicate the identity, or activate deployment. This operation is distinct from application provisioning. Refresh the base what-if after the correction. Source: https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims and https://learn.microsoft.com/en-us/cli/azure/identity/federated-credential.
