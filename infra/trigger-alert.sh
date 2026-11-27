#!/usr/bin/env bash
# Déclenche VOLONTAIREMENT l'alerte de taux d'erreur (issue #10, §4.5 :
# « l'alerte s'est déclenchée au moins une fois »).
#
#   API_URL=https://<api>.azurecontainerapps.io bash infra/trigger-alert.sh
#
# Envoie 30 requêtes invalides (422, aucune donnée client) puis 5 requêtes
# valides. Sur la fenêtre de 15 min, le taux d'erreur dépasse 20 % avec plus de
# 10 appels : l'alerte part à la prochaine évaluation (≤ 15 min, plus quelques
# minutes d'ingestion). Coût : négligeable (35 requêtes).
set -euo pipefail
[[ "${DSCC_ALERT_TEST_APPROVAL:-}" == APPROVED-DSCC-SYNTHETIC-ALERT-TEST ]] || {
  echo "Synthetic alert test not approved; no requests sent." >&2; exit 2;
}
: "${API_URL:?Définir API_URL=https://<api>}"
API_URL="${API_URL%/}"
[[ "$API_URL" =~ ^https://[a-zA-Z0-9.-]+\.azurecontainerapps\.io$ ]] || {
  echo "Expected approved Azure Container Apps HTTPS origin" >&2; exit 2;
}

VALID_ROW='{"customerID":"DEMO-0001","gender":"Female","SeniorCitizen":0,"Partner":"Yes","Dependents":"No","tenure":1,"PhoneService":"No","MultipleLines":"No phone service","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check","MonthlyCharges":29.85,"TotalCharges":29.85}'

# Réveille l'API si elle est à 0 réplica (le premier appel peut être lent).
curl -fsS --max-time 60 "$API_URL/health" > /dev/null && echo "API prête"

for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -H 'Content-Type: application/json' -H "X-DSCC-Blob: alert-test-$i.csv" \
    -d '{"rows": []}' "$API_URL/predict/batch")
  printf 'invalide %02d -> %s\n' "$i" "$code"
  [[ "$code" == 422 ]] || { echo "Unexpected invalid-request status" >&2; exit 1; }
done

for i in $(seq 1 5); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -H 'Content-Type: application/json' -H "X-DSCC-Blob: alert-ok-$i.csv" \
    -d "{\"rows\": [$VALID_ROW]}" "$API_URL/predict/batch")
  printf 'valide   %02d -> %s\n' "$i" "$code"
  [[ "$code" == 200 ]] || { echo "Unexpected valid-request status" >&2; exit 1; }
done

echo "HTTP statuses verified: 30 x 422 and 5 x 200. Alert firing still needs evidence."
echo "Check actual Azure Monitor alert history and notification; do not infer firing from this script."
