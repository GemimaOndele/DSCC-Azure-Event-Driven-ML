# Observabilité — Issue #10 (`feat/observability`, R4)

Objectif du sujet (§4.5) : OpenTelemetry sur l'API et la Function App, **2 métriques
personnalisées** au minimum, **1 alerte** déclenchée volontairement avec notification
e-mail, **3 requêtes KQL** avec captures. Log Analytics plafonné à **0,2 Go/jour**.

## 1. Métriques personnalisées (API)

Instruments OpenTelemetry déclarés dans `api/main.py` et exportés par
`azure-monitor-opentelemetry` vers la table **`customMetrics`** d'Application Insights
(`AppMetrics` dans Log Analytics).

| Métrique | Type | Unité | Sens | Dimensions |
|---|---|---|---|---|
| `inferred_rows` | compteur | clients | **nombre d'inférences** = clients prédits (un lot de *n* lignes ajoute *n*) | `endpoint`, `model_version` |
| `inference_latency_ms` | histogramme | ms | **latence du modèle** (exécution ONNX) | `endpoint`, `model_version` |
| `inference_requests` | compteur | appels | appels HTTP de prédiction réussis (un lot = 1) | `endpoint`, `model_version` |
| `inference_errors` | compteur | appels | rejets/échecs : `validation` (422), `too_large` (413), `model_error`, `model_not_loaded` | `endpoint`, `reason`, `model_version` |

Les deux métriques exigées par le sujet sont `inferred_rows` et `inference_latency_ms`.
Les noms reprennent `inferred_rows`, proposé dans #17 et confirmé ici.

Choix de conception :

- **Dimensions à faible cardinalité** uniquement. Le nom du fichier n'est **jamais** une
  dimension de métrique. Il est attaché au **span de requête** (`dscc.file_name`, issu
  de l'en-tête `X-DSCC-Blob` envoyé par le worker) et aux journaux.
- `GET /metrics` reste disponible, mais ses compteurs sont **en mémoire, par réplica**, et
  repartent de zéro à chaque mise à l'échelle jusqu'à zéro. L'historique fiable est
  celui d'Application Insights.
- `/health` est exclu de l'instrumentation des requêtes : les sondes liveness/readiness
  rempliraient sinon la table `requests` et consommeraient le plafond de 0,2 Go/jour.

### Correctif d'instrumentation

Dans #17, `configure_azure_monitor()` était appelé dans le `lifespan`, donc **après**
`app = FastAPI(...)`. L'instrumentation FastAPI ne s'appliquait pas : aucun span
serveur n'était produit et la table `requests` serait restée vide (vérifié avec un
exportateur en mémoire). La télémétrie est désormais configurée au chargement du module,
et l'application est instrumentée explicitement avec
`FastAPIInstrumentor.instrument_app(app, excluded_urls="health")`. Résultat vérifié :
`POST /predict/batch` → span serveur avec `dscc.file_name` et `http.status_code`.

## 2. Function App (à appliquer dans #6)

Pour que les journaux du worker (`blobName`, `durationMs`, `rows`, `atRisk`) arrivent
dans `traces.customDimensions`, la Function App doit exporter en OpenTelemetry :

- `host.json` : ajouter `"telemetryMode": "OpenTelemetry"` ;
- `requirements.txt` : ajouter `azure-monitor-opentelemetry` ;
- `function_app.py` : appeler `configure_azure_monitor()` avant `app = func.FunctionApp()`,
  si `APPLICATIONINSIGHTS_CONNECTION_STRING` est défini ;
- paramètre d'application `PYTHON_ENABLE_OPENTELEMETRY=true`.

Ces noms de réglages sont à vérifier au moment du déploiement dans la page Microsoft
Learn « Use OpenTelemetry with Azure Functions », qui évolue avec le plan Flex Consumption.

Sans ces réglages, les requêtes ci-dessous fonctionnent quand même, car elles reposent
sur la télémétrie de l'**API**. Seule la variante « bout en bout » de Q2 a besoin des
journaux du worker.

## 3. Requêtes KQL (fichiers dans [`kql/`](kql))

À exécuter dans *Application Insights → Journaux*. Dans *Log Analytics*, les tables
s'appellent `AppRequests` / `AppMetrics` (colonnes `TimeGenerated`, `Name`, `Properties`).

| # | Fichier | Question |
|---|---|---|
| Q1 | [`q1-inferences-par-heure.kql`](kql/q1-inferences-par-heure.kql) | Inférences par heure : clients prédits et appels API |
| Q2 | [`q2-fichiers-les-plus-lents.kql`](kql/q2-fichiers-les-plus-lents.kql) | Les 5 fichiers les plus lents |
| Q3 | [`q3-codes-http-et-erreurs.kql`](kql/q3-codes-http-et-erreurs.kql) | Répartition des codes HTTP et des erreurs par motif |

```kusto
// Q1 — Inférences par heure
customMetrics
| where timestamp > ago(24h)
| where name in ("inferred_rows", "inference_requests")
| summarize clients_predits = sumif(value, name == "inferred_rows"),
            appels_api      = sumif(value, name == "inference_requests")
            by heure = bin(timestamp, 1h)
| order by heure asc
| render columnchart
```

```kusto
// Q2 — Les 5 fichiers les plus lents
requests
| where timestamp > ago(7d)
| where name == "POST /predict/batch"
| extend fichier = tostring(customDimensions["dscc.file_name"])
| where isnotempty(fichier)
| summarize duree_max_ms = max(duration), duree_moy_ms = avg(duration),
            appels = count(), derniere_fois = max(timestamp) by fichier
| top 5 by duree_max_ms desc
```

```kusto
// Q3 — Codes HTTP
requests
| where timestamp > ago(24h)
| summarize appels = count() by name, resultCode
| order by appels desc
| render piechart
```

Variante de Q2 « bout en bout », mesurée côté worker (après l'activation OTel de §2) :

```kusto
traces
| where message == "Inference stored"
| extend fichier = tostring(customDimensions["blobName"]),
         duree_ms = todouble(customDimensions["durationMs"])
| top 5 by duree_ms desc
| project timestamp, fichier, duree_ms, lignes = toint(customDimensions["rows"])
```

## 4. Alerte e-mail

Script : [`infra/observability.sh`](../../infra/observability.sh). Il réutilise exclusivement l'espace de travail et Application Insights déjà déployés par R3 (#24). Il vérifie l'abonnement, le lien entre ressources et le plafond journalier avant toute création d'alerte. L'adresse e-mail est transmise localement via `ALERT_EMAIL`.

- **Type** : alerte de recherche dans les journaux, évaluée **toutes les 15 min** sur
  15 min (option la moins chère recommandée par le sujet), gravité 2, résolution
  automatique.
- **Condition** (fichier [`kql/alerte-taux-erreur.kql`](kql/alerte-taux-erreur.kql)) :
  au moins 10 appels de prédiction **et** (taux d'erreur > 20 % **ou** latence p95 > 1 s).
- **Notification** : groupe d'actions configurable (par défaut `dscc-alerts`) → e-mail.

### Déclenchement volontaire

```bash
# Après approbation explicite du propriétaire et vérification du budget :
export DSCC_SUBSCRIPTION="<abonnement choisi>"
export DSCC_RG="<groupe R3 existant>"
export DSCC_FUNCTION="<Function App existante>"
export ALERT_EMAIL="<adresse approuvée>"
DSCC_ALERT_APPROVAL=APPROVED-DSCC-ALERT bash infra/observability.sh
# Autorisation distincte pour le trafic de test :
DSCC_ALERT_TEST_APPROVAL=APPROVED-DSCC-SYNTHETIC-ALERT-TEST \
  API_URL="https://<app>.azurecontainerapps.io" bash infra/trigger-alert.sh
```

L'état *Fired* et l'e-mail doivent être constatés dans Azure ; aucun déclenchement n'est garanti par les seuls codes HTTP. Le script s'arrête si une requête ne renvoie pas le code attendu. Les extensions CLI nécessaires doivent être disponibles avant exécution.

## 5. Preuves à capturer pour le rapport

- [ ] *Application Insights → Métriques* : `inferred_rows` et `inference_latency_ms`
  (espace de noms « azure.applicationinsights » / métriques personnalisées).
- [ ] Résultat de Q1, Q2 et Q3 avec la requête visible (sans identifiant sensible).
- [ ] Règle d'alerte (condition, fréquence 15 min, groupe d'actions).
- [ ] Alerte à l'état **Fired** dans *Azure Monitor → Alertes*, et l'**e-mail reçu**
  (adresse masquée).
- [ ] Plafond journalier de l'espace : *Log Analytics → Utilisation et coûts estimés →
  Limite quotidienne = 0,2 Go*.

## 6. Tests

`api/tests/test_telemetry.py` remplace Azure Monitor par un lecteur OpenTelemetry en
mémoire et vérifie exactement ce qui serait exporté :

- `/predict` + lot de 3 lignes → `inferred_rows` +1 / +3, `inference_requests` +1 / +1,
  un échantillon de latence par appel ;
- 422 de validation (Pydantic et `NaN` filtré par le middleware) → `inference_errors`
  avec `reason=validation`, aucune ligne comptée ; un 404 sur une autre route n'est pas
  compté.

### Contrôles hors cloud

`bash tests/observability/test_guards.sh` utilise uniquement des doubles de commandes Azure CLI et curl. Aucun appel Azure réel. Le contrôle vérifie les autorisations, l'absence de création d'une seconde ressource de monitoring et les codes 422/200 attendus.

## Integration boundary — 27 November

The API instrumentation and its tests are now owned exclusively by #17. This R4 branch is explicitly stacked on R1 #17 (846a697), and its delta relative to that commit contains only the observability runbook, KQL, guarded scripts and independent checks. R1 files are inherited byte-for-byte, not edited or duplicated as a second implementation. The PR against main will include the inherited files until #17 is integrated. Integrate #17 before #20; do not merge #20 first. The synthetic alert request targets the 19-feature model 1.1.0; it does not prove Azure telemetry or alert delivery. R1 tests run in #17/#23, not in this R4-only branch. No live alert was triggered.
