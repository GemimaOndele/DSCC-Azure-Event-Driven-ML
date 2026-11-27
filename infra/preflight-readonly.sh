#!/usr/bin/env bash
# Read-only Azure preflight. Run in authenticated Cloud Shell / local Azure CLI.
# No provider registration, resource creation, role assignment or deployment.
set -euo pipefail

command -v az >/dev/null || { echo "Azure CLI required" >&2; exit 1; }
az account show --query '{subscription:name,state:state}' -o table
SUB="$(az account show --query id -o tsv)"
test -n "$SUB"
printf '\nProvider registration (do not register automatically):\n'
for provider in Microsoft.Storage Microsoft.Web Microsoft.App Microsoft.DocumentDB Microsoft.EventGrid Microsoft.Insights Microsoft.OperationalInsights Microsoft.ManagedIdentity; do
  az provider show --namespace "$provider" --query '{provider:namespace,state:registrationState}' -o table
done

printf '\nFlex Consumption available locations:\n'
az functionapp list-flexconsumption-locations -o table
printf '\nContainer Apps environment locations:\n'
az provider show --namespace Microsoft.App --query "resourceTypes[?resourceType=='managedEnvironments'].locations | [0]" -o json
printf '\nCosmos DB account locations:\n'
az provider show --namespace Microsoft.DocumentDB --query "resourceTypes[?resourceType=='databaseAccounts'].locations | [0]" -o json

printf '\nPolicy assignments at subscription scope (may require extra read permission):\n'
az policy assignment list --scope "/subscriptions/$SUB" --query '[].{displayName:displayName,parameters:parameters}' -o json
printf '\nExisting Cosmos DB accounts and free-tier setting (if permitted):\n'
az cosmosdb list --query '[].{location:location,freeTier:enableFreeTier}' -o table
printf '\nCheck in Portal: actual remaining student credits, allowed regions including inherited policy, Flex/Container Apps regional quota, Cosmos free-tier entitlement, Cost Analysis and budgets.\n'
printf 'Do not share subscription IDs, identities, private policy parameters or customer data.\n'
