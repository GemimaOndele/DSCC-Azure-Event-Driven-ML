# Azure preflight and approval checklist — #3 / #7 / #8

Prepared 26 November 2026. **No Azure resources created; no verified live balance,
quota, subscription selection or region.** Run the read-only script in the owner's
authenticated Cloud Shell, separately for both student subscriptions.

```bash
bash infra/preflight-readonly.sh
```

Record only non-sensitive results in the team evidence register:

| Control | Gémima | Aminata | Decision/evidence |
|---|---|---|---|
| Remaining Azure for Students credit and expiry | Pending | Pending | Portal |
| Allowed regions including inherited policy | Pending | Pending | Policy assignment / Resource Graph |
| Flex Consumption Python 3.12 and quota | Pending | Pending | CLI + quota portal |
| Container Apps consumption capacity / quota | Pending | Pending | Portal |
| Cosmos DB Free Tier available | Pending | Pending | Portal / existing accounts |
| Subscription owner and guest/Contributor permissions | Pending | Pending | Owner validation |
| Budget ≤ USD 25, alert thresholds 20/50/80% | Pending | Pending | Cost Management approval |
| Chosen region and deployment date | Pending | Pending | Team decision |

## Proposed resource inventory (not deployed)
- One tagged resource group. Cosmos DB Free Tier first if eligible, partition
  key /fileName and database pipeline / container inferences; Table Storage
  fallback only after explicit decision.
- Storage LRS: input, output, rejected, models; inference-requests queue and
  poison queue; static site $web. Versioned output names proposed in #21.
- Flex Consumption Python 3.12, target 512 MiB subject to quota and test;
  system/user managed identity; host storage and deployment storage must
  be configured for Flex. Queue sender and host use Base64.
- Container Apps consumption: 0.25 vCPU, 0.5 GiB, min 0 max 2 replicas;
  verify startup/memory requirements of ONNX runtime; use one environment.
- Application Insights / Log Analytics 0.2 GB/day cap, alert policy from #20.
- Event Grid subscription filtered to input BlobCreated only, after dispatcher
  is deployed; do not expose event subscription endpoint keys.
- UAMI for GitHub Actions federated credential, constrained to production
  environment and this repository; Contributor only at project RG.
- Managed identity data-plane roles for Storage Blob/Queue, Table if used, and
  Cosmos data contributor with correct scope; role assignment requires owner.
- GHCR registry pull configuration is a separate prerequisite: private registry
  may require approved scoped read credential stored only as an Azure secret.
  Never change package visibility without dataset/artifact publication approval.
  Azure UAMI OIDC for ARM does not automatically grant GHCR access.

## Cost and security gates
A budget alert does not stop consumption. Verify all pricing/region availability,
check actual credits and set alerts before provision. No VM, GPU, Kubernetes,
always-on replica or unapproved paid registry. Track real spend daily.
After the defense, separately authorize cleanup and record resource-group absence
and any remaining service-created resource groups. No cleanup is executed here.

Reference: docs/azure-access-guide.md in main; Microsoft Learn Flex Consumption
deployment: https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to
and Container Apps GHCR: https://learn.microsoft.com/en-us/azure/container-apps/github-actions
