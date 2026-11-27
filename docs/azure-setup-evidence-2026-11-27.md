# Azure setup evidence — 27 November 2026

This is an evidence addendum to `docs/final-report-draft.md` (PR #25). It records observed results, not a completed application deployment. Screenshots are retained locally in `rapport-preuves-azure/`; do not publish raw identifiers or personal account details.

## Observed results

| Item | Verified result |
|---|---|
| Subscription | Owner's Azure for Students selected, active; owner has Owner role |
| Region policy | francecentral permitted; other permitted regions: denmarkeast, austriaeast, spaincentral, germanywestcentral |
| Existing resources before DSCC | Log Analytics workspace and Network Watcher; no Cosmos DB account returned |
| Providers | Microsoft.App and Microsoft.EventGrid registered; other six required providers already registered |
| Container Apps quota | France Central managed environments: 0 used / 1 allowed |
| Flex availability | francecentral returned by list-flexconsumption-locations; memory quota still unverified |
| Project group | rg-projet-g2cc created, France Central; project=DSCC, purpose=academic-demo |
| Budget | budget-dscc-surveillance, 4 EUR/month, actual-cost alerts 20/50/80% to owner; 0 EUR evaluated when checked |
| Budget limits | Alerts do not stop spend; monthly reset does not enforce the USD25 total ceiling; target remains <USD5 |
| Base simulation | base.bicep at a981b2626deab860139b143a6b4029ce56a7998d; Succeeded, 23 Create, error null |
| Proposed names | dsccg2cc20261126 Storage available; dscc-g2cc-20261126 Cosmos name not in use when checked |
| Azure GitHub identity | dscc-github-mi created; github-production federation created |
| Federation | GitHub issuer; repo:GemimaOndele/DSCC-Azure-Event-Driven-ML:environment:production subject; api://AzureADTokenExchange audience |
| Azure permission | Contributor assigned and read back at the project RG only |
| Production protection | Owner approval required, administrator bypass disabled, only main branch allowed |
| Connection variables | AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP populated in production; values deliberately omitted here |
| Deployment switch | AZURE_DEPLOY_ENABLED=false in production and at repository level |
| Main protection | Creation confirmed after owner's personal GitHub reauthentication; PR + one approval + resolved conversations, no admin bypass, force push or branch deletion |
| Credential handling | Owner authenticated directly; no password, token, MFA code or permanent Azure client secret shared or committed |

## Reproducible read-only checks

```bash
az account show --query '{name:name,state:state}' -o table
az cosmosdb list --query '[].{name:name,freeTier:enableFreeTier,location:location}' -o table
az functionapp list-flexconsumption-locations --query "[?name=='francecentral']" -o json
az storage account check-name --name dsccg2cc20261126 -o json
az cosmosdb check-name-exists --name dscc-g2cc-20261126 -o json
az deployment group what-if --resource-group rg-projet-g2cc --name dscc-base \
  --template-file dscc-plan/base.bicep \
  --parameters location=francecentral storageName=dsccg2cc20261126 \
  cosmosName=dscc-g2cc-20261126 resultBackend=cosmosFreeTier prefix=dscc \
  --result-format ResourceIdOnly --no-pretty-print
```

The original plan predates creation of the GitHub identity/federation/role. Run a new what-if before application; 23 Create is historical, not the current remaining count. The role assignment name was calculated with ARM-compatible UUIDv5 inputs matching base.bicep to avoid duplication.

## Screenshot register

1. 01-fournisseurs-avant-inscription.jpg — provider inventory before registration.
2. 02-container-apps-inscription-en-cours.jpg — intermediate registration; not a success claim.
3. 03-container-apps-registered.jpg — Container Apps registered.
4. 04-quotas-container-apps-francecentral.jpg — regional quota.
5. 05-groupe-dscc-vide.jpg — group with no resources immediately after creation.
6. 06-budget-dscc-cree.jpg — budget recorded.
7. 07-what-if-succeeded.jpg — simulation summary, 23 creates, no apply.
8. 08-github-production-configure.jpg — production protections and variables.
9. 09-main-protection-creee.jpg — main protection created.

Some early screenshots have a narrow crop. Use the observed text and corresponding checkpoint for interpretation; do not stretch them into evidence of a deployment. Review identifiers and account details before distributing screenshots.

## Limits and unfinished acceptance

- No base deployment of Storage, Cosmos, monitoring or runtime identity was executed.
- No Function App, Container App, Event Grid subscription, dashboard or model was deployed.
- Cosmos Free Tier eligibility still needs explicit validation at creation; absence of accounts and a successful what-if are insufficient guarantees.
- Flex regional memory quota is unverified: the tested usages API returned MethodNotAllowed/51009.
- No priced workload estimate or total-cost acceptance was completed.
- Individual team Azure roles are not configured; exact accounts and scopes remain to be verified.
- OIDC configuration is in place but a GitHub-issued token has not yet been tested end-to-end.
- PR #23 now contains a read-only OIDC verification workflow, guarded to main and production approval. It must be reviewed/integrated by humans before manual execution. The agent did not merge or approve any PR or deployment.
- Dataset/artifact rights and final release remain decision gates; no model publication permission is inferred.
- The academic report remains a draft until deployment, real E2E acceptance, costs, and release decisions are evidenced.

## Resume without relying on this browser session

Read this addendum and PR #24 checkpoints. Keep deployment disabled. After human integration of the read-only workflow, the owner can run it on main with READ-DSCC and manually approve production; it performs Azure reads only. Use GitHub Actions for repeatable verification. Complete quota/cost/Free Tier checks and refresh the base plan before any resource deployment. Keep deployment and data rights decisions explicit. Browser account login and deployment approval remain personal actions; no handoff document grants an assistant new tools or permissions.
