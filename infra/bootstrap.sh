#!/usr/bin/env bash
# Human-operated bootstrap. Default: show help. No Azure resource operation until
# a phase and explicit approval are supplied. Do not run this in PR CI.
set -euo pipefail

usage() {
  cat <<'HELP'
Usage: bash infra/bootstrap.sh <plan-base|apply-base|plan-apps|apply-apps|connect-event-grid>
Required for any Azure operation:
  DSCC_SUBSCRIPTION, DSCC_RG (e.g. rg-projet-g2cc), DSCC_REGION
  DSCC_STORAGE, DSCC_COSMOS, DSCC_BACKEND (cosmosFreeTier or table)
  DSCC_PREFIX (default dscc)
For apps: DSCC_FUNCTION, DSCC_IMAGE (approved GHCR digest), DSCC_REGISTRY_MODE
  (public/private), DSCC_COSMOS_ENDPOINT, DSCC_DASHBOARD_ORIGIN.
For apply or connect: DSCC_APPROVAL=APPROVED-DSCC-BUDGET-25
The selected owner must confirm budget and alerts, regions, quota, permissions
and backend. For app deployment, additionally confirm artifact rights and
temporary synthetic-only public endpoints. Plans require an existing RG and
make Azure what-if requests only. No subscription switching is performed.
HELP
}
phase="${1:---help}"
case "$phase" in
  --help|-h|help) usage; exit 0 ;;
  plan-base|plan-apps) ;;
  apply-base|apply-apps|connect-event-grid)
    [[ "${DSCC_APPROVAL:-}" == APPROVED-DSCC-BUDGET-25 ]] || {
      echo "Missing explicit owner approval; nothing executed." >&2; exit 2;
    } ;;
  *) usage >&2; exit 2 ;;
esac
: "${DSCC_SUBSCRIPTION:?Set selected subscription locally}"
: "${DSCC_RG:?Set project resource group}"
: "${DSCC_REGION:?Set verified region}"
: "${DSCC_STORAGE:?Set unique storage name}"
: "${DSCC_COSMOS:?Set unique Cosmos name}"
: "${DSCC_BACKEND:?Choose result backend explicitly}"
prefix="${DSCC_PREFIX:-dscc}"
[[ "$DSCC_BACKEND" == cosmosFreeTier || "$DSCC_BACKEND" == table ]] || exit 2
[[ "$DSCC_STORAGE" =~ ^[a-z0-9]{3,24}$ ]] || { echo "Invalid storage name"; exit 2; }
[[ "$prefix" =~ ^[a-z][a-z0-9-]{1,14}$ ]] || { echo "Invalid prefix"; exit 2; }
[[ "$(az account show --query id -o tsv)" == "$DSCC_SUBSCRIPTION" ]] || {
  echo "Wrong Azure subscription. Nothing executed." >&2; exit 2;
}
[[ "$(az group exists --name "$DSCC_RG")" == true ]] || {
  echo "Create the approved project RG separately as owner, then configure its budget." >&2; exit 2;
}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$phase" == plan-base || "$phase" == apply-base ]]; then
  action=what-if
  [[ "$phase" != apply-base ]] || action=create
  az deployment group "$action" --resource-group "$DSCC_RG" --name dscc-base \
    --template-file "$ROOT/base.bicep" --parameters location="$DSCC_REGION" \
      storageName="$DSCC_STORAGE" cosmosName="$DSCC_COSMOS" resultBackend="$DSCC_BACKEND" prefix="$prefix" \
    --only-show-errors
  exit
fi
: "${DSCC_FUNCTION:?Set unique function name}"
if [[ "$phase" == connect-event-grid ]]; then
  # Only after deployed dispatcher is listed and the team accepts event delivery.
  function_id="$(az functionapp function show -g "$DSCC_RG" -n "$DSCC_FUNCTION" --function-name dispatcher --query id -o tsv)"
  [[ "$function_id" == */functions/dispatcher ]] || { echo "Dispatcher not deployed"; exit 2; }
  storage_id="$(az storage account show -g "$DSCC_RG" -n "$DSCC_STORAGE" --query id -o tsv)"
  az eventgrid event-subscription create --name "$prefix-input-created" \
    --source-resource-id "$storage_id" --endpoint-type azurefunction --endpoint "$function_id" \
    --included-event-types Microsoft.Storage.BlobCreated \
    --subject-begins-with /blobServices/default/containers/input/blobs/ \
    --subject-ends-with .csv --only-show-errors --output none
  echo "Event subscription configured; actual delivery still needs E2E proof."
  exit
fi
: "${DSCC_IMAGE:?Use approved GHCR digest}"
: "${DSCC_REGISTRY_MODE:?Choose public or private explicitly}"
[[ "$DSCC_IMAGE" =~ ^ghcr\.io/gemimaondele/dscc-azure-event-driven-ml/churn-api@sha256:[a-f0-9]{64}$ ]] || {
  echo "Expected approved project image digest"; exit 2;
}
[[ "$DSCC_REGISTRY_MODE" == public || "$DSCC_REGISTRY_MODE" == private ]] || exit 2
[[ "${DSCC_EXPOSURE_APPROVAL:-}" == approved-synthetic-demo ]] || {
  echo "Temporary public synthetic-only demo not approved."; exit 2;
}
if [[ "$DSCC_BACKEND" == cosmosFreeTier ]]; then
  : "${DSCC_COSMOS_ENDPOINT:?Cosmos endpoint from base deployment required}"
else
  [[ -z "${DSCC_COSMOS_ENDPOINT:-}" ]] || { echo "Table mode must not set Cosmos endpoint"; exit 2; }
fi
action=what-if
[[ "$phase" != apply-apps ]] || action=create
# Use a private 0600 local JSON parameter file for secure registry credential.
# No password in process args, GitHub or console. Clean it after the command.
umask 077
params="$(mktemp)"
trap 'rm -f "$params"' EXIT
export DSCC_REGION DSCC_STORAGE DSCC_FUNCTION DSCC_IMAGE DSCC_REGISTRY_MODE DSCC_COSMOS_ENDPOINT="${DSCC_COSMOS_ENDPOINT:-}" DSCC_DASHBOARD_ORIGIN="${DSCC_DASHBOARD_ORIGIN:-}" DSCC_EXPOSURE_APPROVAL
export DSCC_PREFIX="$prefix"
python3 - "$params" <<'PY'
import getpass
import json
import os
import sys
mapping = {
    "location": "DSCC_REGION", "storageName": "DSCC_STORAGE", "prefix": "DSCC_PREFIX",
    "functionName": "DSCC_FUNCTION", "apiImage": "DSCC_IMAGE",
    "registryMode": "DSCC_REGISTRY_MODE", "cosmosEndpoint": "DSCC_COSMOS_ENDPOINT",
    "dashboardOrigin": "DSCC_DASHBOARD_ORIGIN", "exposureApproval": "DSCC_EXPOSURE_APPROVAL",
}
values = {k: {"value": os.environ[v]} for k,v in mapping.items()}
if os.environ["DSCC_REGISTRY_MODE"] == "private":
    with open("/dev/tty", "r+") as tty:
        tty.write("Approved GHCR read-only user: "); tty.flush()
        user = tty.readline().strip()
    password = getpass.getpass("Approved scoped GHCR read token (not echoed): ")
    if not user or not password:
        raise SystemExit("Missing registry credential")
    values["registryUsername"] = {"value": user}
    values["registryPassword"] = {"value": password}
with open(sys.argv[1], "w") as file:
    json.dump({"$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
               "contentVersion": "1.0.0.0", "parameters": values}, file)
PY
az deployment group "$action" --resource-group "$DSCC_RG" --name dscc-apps \
  --template-file "$ROOT/apps.bicep" --parameters @"$params" --only-show-errors
