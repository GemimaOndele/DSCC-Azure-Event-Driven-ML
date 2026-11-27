# France Central — preliminary demo cost and readiness, 27 November 2026

This estimate uses the Microsoft public USD retail-price snapshot dated
27 November 2026 provided in the handoff archive, not the subscription's invoice.
Workload assumptions below are planning assumptions, not measured usage.
The project owner has selected Azure for Students in France Central. The RG,
EUR 4/month budget with 20/50/80% alerts, GitHub UAMI, federation and RG-scoped
Contributor are reported created in the Work evidence addendum. No base/apply
or actual end-to-end OIDC login has been evidenced.

## Seven-day bounded demonstration (27 Nov–3 Dec, then separately approved cleanup)

Conservative charge calculation ignores free monthly grants for Functions,
Container Apps and Analytics Logs; assumes Consumption only, no always-ready,
no Dedicated workload or private endpoint, no additional retention/export.
Cosmos zero is conditional on successful Free Tier creation (400 shared RU/s,
one region, storage below 25 GB); do not silently create paid Cosmos.

| Item | Assumed maximum normal-demo volume | Retail tariff from snapshot | USD |
|---|---|---|---:|
| Hot Blob LRS | 1 GB-month (conservative full month) | $0.0192/GB-month | 0.0192 |
| Blob write | 20,000 operations | $0.059/10k | 0.1180 |
| Blob read | 20,000 operations | $0.0047/10k | 0.0094 |
| Queue v2 LRS | 0.1 GB-month + 100,000 operations | $0.045/GB-month; $0.004/10k | 0.0445 |
| Functions Flex on demand | 1,000 invocations, 5 s average, 512 MB | $0.000026/GB-s; $0.000004/10 executions | 0.0654 |
| Container Apps active | 4 aggregate replica-hours, 0.25 vCPU, 0.5 GiB | $0.000024/vCPU-s; $0.000003/GiB-s | 0.1080 |
| Container Apps requests | 1,000 | $0.40/million | 0.0004 |
| Analytics Logs | 0.2 GB TOTAL during seven-day window | $2.76/GB above allowance; charge full volume in estimate | 0.5520 |
| One 15-min log alert | One rule, provisionally full monthly price | $0.50/month system log meter | 0.5000 |
| Cosmos DB | 400 shared RU/s, Free Tier confirmed at creation | Conditional free tier | 0.0000 |
| **Priced subtotal** | | | **1.4179** |
| Planning contingency | Event Grid, host/deployment operations, DNS/network, possible alert dimensions/email or unlisted meters | Allowance, not quote | 1.0000 |
| **Preliminary planning total** | | | **2.4179** |

The Event Grid Basic free grant is 100,000 monthly operations; this planning
scenario assumes small traffic well below it, but actual subscription eligibility
and consumption must be confirmed. No additional free grants are subtracted in
the subtotal. Not all meters are in the provided snapshot. An extra USD 1 is a
planning reserve, not a verified ceiling. The 4 EUR monthly budget is not a
hard spending cap, and November/December usage must be added together.

**Stress case:** the existing 0.2 GB/day Log Analytics cap can permit 1.4 GB
over seven days, or USD 3.864 at the above marginal rate. Substituting this
for USD 0.552 yields USD 4.7299 before reserve, USD 5.7299 with reserve.
The target <USD 5 is plausible for the normal scenario but not guaranteed.
Review daily ingestion, actual credit usage, alert billing and scaling; stop
unneeded traffic promptly. Owner approval is required before provisioning
or changing caps/alerts. Keep USD 25 total ceiling. No paid resources were
created in producing this estimate.

## Remaining subscription checks

- Flex: France Central availability is observed, actual regional quota is not.
  Previous usages API returned MethodNotAllowed/51009, not zero quota. Microsoft
  documents the Flex Consumption Quota diagnostic in an existing Function App:
  Diagnose and solve problems → Flex Consumption Quota → region. If no app exists,
  seek quota confirmation from Azure support / portal before relying on capacity;
  do not infer actual student quota from public defaults. At 40 configured maximum
  instances × 512 MB, this plan can use 20,480 MB and 10 typical cores if fully
  scaled; this is a sizing calculation, not measured regional capacity.
- Cosmos: only one Free Tier per subscription, opt-in at creation; 1,000 RU/s and
  25 GB are free when applicable. Empty inventory and initial what-if are
  encouraging but do not prove eligibility. Verify the free-tier option and
  no paid fallback; if unavailable, return to the team for explicit Table
  fallback decision and separate costing.
- Container Apps: observed managed-environment count 0/1 is not vCPU quota.
  Check consumption cores and actual available capacity before app deployment.
- Refresh the base what-if because the UAMI/federation/RG role already exist.
  Check unchanged resources, no duplicates, and no unexpected paid service.
- OIDC: an identical copy of the previously linted azure-oidc-readonly.yml is
  included in #24 so this infrastructure PR can be integrated first without
  the ML PRs or the full CI/CD workflow. On approved main, dispatch READ-DSCC
  and the owner approves production personally. Keep AZURE_DEPLOY_ENABLED=false.
  Successful read-only login proves scope/access, not resource deployment.
  The same file in #23 is intentional and byte-identical; retain one copy at
  the same path on integration. Refresh the ten-open-PR gate after first merge.
- RBAC: the GitHub identity's RG Contributor role cannot assign Azure roles.
  Owner must execute/approve the first Bicep deployment that creates role
  assignments. Do not elevate the CI identity to Owner or User Access Administrator.

## Sources
- Azure retail snapshot in handoff archive, region francecentral, USD, 27 Nov 2026.
- https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan
- https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier
- https://azure.microsoft.com/en-us/pricing/details/functions/
- https://azure.microsoft.com/en-us/pricing/details/container-apps/
- https://azure.microsoft.com/en-us/pricing/details/event-grid/
- https://azure.microsoft.com/en-us/pricing/details/monitor/
