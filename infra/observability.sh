#!/usr/bin/env bash
# R4 — configure alerts on existing R3 resources only.
# No workspace, App Insights or app creation. Requires owner budget approval.
set -euo pipefail

[[ "${DSCC_ALERT_APPROVAL:-}" == APPROVED-DSCC-ALERT ]] || {
  echo "Missing approval for potentially billable alert; no Azure operation." >&2; exit 2;
}
: "${DSCC_SUBSCRIPTION:?Selected subscription required}"
: "${DSCC_RG:?Project RG required}"
: "${DSCC_FUNCTION:?Existing Function App name required}"
: "${ALERT_EMAIL:?Alert recipient required}"
EQ="${DSCC_PREFIX:-dscc}"
RG="$DSCC_RG"
LAW="${DSCC_LOG_WORKSPACE:-$EQ-logs}"
AI="${DSCC_INSIGHTS:-$EQ-insights}"
API="${DSCC_CONTAINER_APP:-$EQ-api}"
FUNC="$DSCC_FUNCTION"
AG="${DSCC_ACTION_GROUP:-$EQ-alerts}"
ALERT="${DSCC_ALERT_NAME:-$EQ-api-errors-latency}"

[[ "$(az account show --query id -o tsv)" == "$DSCC_SUBSCRIPTION" ]] || {
  echo "Wrong subscription; no alert created." >&2; exit 2;
}
# Fail closed on missing resources. Extensions must already be installed.
LAW_ID="$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)"
AI_ID="$(az monitor app-insights component show -g "$RG" --app "$AI" --query id -o tsv)"
AI_WORKSPACE="$(az monitor app-insights component show -g "$RG" --app "$AI" --query workspaceResourceId -o tsv)"
[[ -n "$LAW_ID" && -n "$AI_ID" && "${AI_WORKSPACE,,}" == "${LAW_ID,,}" ]] || {
  echo "Application Insights is not linked to the approved workspace." >&2; exit 2;
}
az containerapp show -g "$RG" -n "$API" --query name -o tsv >/dev/null
az functionapp show -g "$RG" -n "$FUNC" --query name -o tsv >/dev/null
# Bicep #24 already configures the 0.2 GB/day cap and both apps' telemetry.
# Read and verify rather than overwrite existing application settings.
quota="$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query workspaceCapping.dailyQuotaGb -o tsv)"
python3 - "$quota" <<'PY'
import sys
q = float(sys.argv[1])
if not 0 < q <= 0.2:
    raise SystemExit("Unexpected workspace cap; ask R3 before proceeding.")
PY

# 4. Groupe d'actions : notification par e-mail.
az monitor action-group create -g "$RG" -n "$AG" --short-name dscc \
  --action email equipe "$ALERT_EMAIL" --tags projet=dscc equipe="$EQ" -o none
AG_ID=$(az monitor action-group show -g "$RG" -n "$AG" --query id -o tsv)

# 5. Alerte de journal, évaluée toutes les 15 min sur 15 min (§4.5) :
#    taux d'erreur des appels de prédiction > 20 % OU latence p95 > 1 s,
#    avec au moins 10 appels pour éviter les faux positifs à très faible trafic.
#    Même requête que docs/observability/kql/alerte-taux-erreur.kql.
ALERT_QUERY='requests
| where name in ("POST /predict", "POST /predict/batch")
| summarize total = count(), echecs = countif(toint(resultCode) >= 400), p95_ms = percentile(duration, 95)
| extend taux_erreur = todouble(echecs) / total
| where total >= 10 and (taux_erreur > 0.2 or p95_ms > 1000)'

az monitor scheduled-query create -g "$RG" -n "$ALERT" --scopes "$AI_ID" \
  --description "DSCC : taux d'erreur > 20 % ou p95 > 1 s sur /predict (15 min)" \
  --condition "count 'Seuil' > 0" \
  --condition-query "Seuil=$ALERT_QUERY" \
  --evaluation-frequency 15m --window-size 15m --severity 2 \
  --action-groups "$AG_ID" --auto-mitigate true \
  --tags projet=dscc equipe="$EQ" -o none

echo "Observabilité configurée : $LAW (0,2 Go/jour), $AI, $AG, $ALERT"
echo "Déclenchement volontaire séparé : voir infra/trigger-alert.sh et son approbation explicite."
