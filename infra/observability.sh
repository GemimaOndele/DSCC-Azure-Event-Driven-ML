#!/usr/bin/env bash
# Observabilité DSCC (issue #10, R4) — à exécuter UNE FOIS dans l'abonnement
# d'intégration, après les commandes de référence du sujet (§6) et la création
# de l'API Container Apps et de la Function App (#7).
#
# Ce script ne contient AUCUN secret : l'adresse e-mail de l'alerte et le nom de
# l'équipe sont passés en variables d'environnement au moment de l'exécution.
#
#   EQ=<equipe> ALERT_EMAIL=<adresse> bash infra/observability.sh
#
# Coût attendu : ingestion < 5 Go/mois (gratuit), plafond 0,2 Go/jour ;
# une règle d'alerte de journal évaluée toutes les 15 min (quelques centimes/mois).
# Suppression : tout est dans rg-projet-$EQ et part avec `az group delete`.
set -euo pipefail

: "${EQ:?Définir EQ=<equipe>}"
: "${ALERT_EMAIL:?Définir ALERT_EMAIL=<adresse e-mail de notification>}"
LOC="${LOC:-$(az group show -n "rg-projet-$EQ" --query location -o tsv)}"
RG="rg-projet-$EQ"
LAW="log-$EQ"
AI="appi-$EQ"
API="api-$EQ"
FUNC="func-$EQ"
AG="ag-dscc-$EQ"
ALERT="alert-api-erreurs-latence-$EQ"

az extension add --name application-insights --upgrade --only-show-errors
az extension add --name scheduled-query --upgrade --only-show-errors

# 1. Espace Log Analytics plafonné à 0,2 Go/jour + Application Insights basé sur
#    cet espace, tous deux DANS le groupe du projet (§4.5). Idempotent.
if ! az monitor log-analytics workspace show -g "$RG" -n "$LAW" -o none 2>/dev/null; then
  az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" --quota 0.2
fi
az monitor log-analytics workspace update -g "$RG" -n "$LAW" --quota 0.2 -o none
LAW_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)

if ! az monitor app-insights component show -g "$RG" --app "$AI" -o none 2>/dev/null; then
  az monitor app-insights component create --app "$AI" -g "$RG" -l "$LOC" --workspace "$LAW_ID"
fi
AI_ID=$(az monitor app-insights component show -g "$RG" --app "$AI" --query id -o tsv)

# 2. Raccorder l'API (Container Apps). La chaîne de connexion n'est pas un mot de
#    passe, mais on la garde en secret Container Apps plutôt qu'en clair.
#    Elle n'est jamais écrite dans le dépôt ni affichée par ce script.
AI_CS=$(az monitor app-insights component show -g "$RG" --app "$AI" --query connectionString -o tsv)
az containerapp secret set -n "$API" -g "$RG" --secrets "appinsights-cs=$AI_CS" -o none
az containerapp update -n "$API" -g "$RG" \
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-cs" -o none

# 3. Raccorder la Function App (déjà fait si elle a été créée avec --app-insights).
az functionapp config appsettings set -n "$FUNC" -g "$RG" \
  --settings "APPLICATIONINSIGHTS_CONNECTION_STRING=$AI_CS" -o none
unset AI_CS

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
echo "Déclenchement volontaire : API_URL=https://<api> bash infra/trigger-alert.sh"
