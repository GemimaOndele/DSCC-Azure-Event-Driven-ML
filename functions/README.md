# Pipeline d'événements — Issue #6 (`feat/event-pipeline`)

Une seule Function App Python 3.12 (modèle de programmation v2) contenant trois functions.
Aucune ressource Azure n'est créée par ce dépôt : le code est testable en local avec Azurite
et l'API `feat/ml-api` lancée sur `localhost:8000`.

## Flux

```
Blob input/<fichier>.csv
  → Event Grid BlobCreated
  → dispatcher (validation .csv, ≤ 1 MiB, 22 colonnes)
  → Queue inference-requests
  → worker (POST /predict/batch, timeout 10 s, idempotence blobName+etag)
  → Blob output/<fichier>.csv.<idempotencyKey>.json + Cosmos DB pipeline/inferences (repli Table Storage)
  → GET /api/recent (20 derniers) → tableau de bord statique $web
```

Fichiers invalides : copie dans `rejected/<fichier>.csv.reason.json` avec un motif lisible,
sans retry. Erreurs transitoires (429/5xx/timeout) : 5 livraisons max
(`host.json` → `maxDequeueCount: 5`), puis `inference-requests-poison`.

## Contrats appliqués

- `contract/features.json` : copie du fichier partagé livré dans #17/#18 (`customerID` +
  **21 features**, `Churn` jamais envoyé, seuil 0,5). Le validateur échoue si le CSV
  comporte une colonne manquante ou supplémentaire, car l'API utilise `extra="forbid"`.
- Lignes entièrement vides ignorées ; `TotalCharges` vide → `null` (imputation médiane
  côté API). Les autres champs obligatoires ne peuvent pas être vides.
- Message de file : `{"blobName","etag","size","enqueuedAt"}` exactement (contrat #14 §3).
- Clé d'idempotence : `<stem>-<sha256(blobName|etag)[:16]>`, stable entre reprises et
  sûre pour un `id` Cosmos DB. Le stockage `output/` crée un objet immuable par version (écriture conditionnelle sans overwrite).
- Métadonnées Cosmos : `id`, `fileName`, `timestamp`, `rows`, `atRisk`,
  `avgChurnProbability`, `modelVersion`, `durationMs`, `status`, `etag`, `idempotencyKey`.
- `GET /api/recent` est anonyme mais n'expose l'en-tête CORS **que** pour l'origine
  exacte `DASHBOARD_ORIGIN`.

## Sécurité

- `DefaultAzureCredential` partout (identité managée) : **aucune clé, mot de passe ou
  connection string** dans le dépôt. `UseDevelopmentStorage=true` dans l'exemple local
  est le compte well-known d'Azurite, pas un secret.
- `api_client.py` ne conserve que le statut HTTP, jamais le corps (données clients).
- Le worker garde un seul client httpx par processus (`get_clients` mis en cache).

## Exécution locale

```bash
py -3.12 -m pip install -r functions/requirements.txt
py -3.12 -m pip install pytest
copy functions\local.settings.json.example functions\local.settings.json
azurite --blobHost 127.0.0.1 --queueHost 127.0.0.1
# API locale : uvicorn api.main:app --port 8000 (branche feat/ml-api)
func start --script-root functions --port 7071
py -3.12 -m pytest functions -q
```

Les tests unitaires n'ont besoin d'aucun service : ils utilisent les adaptateurs en
mémoire de `tests/fakes.py` et `httpx.MockTransport`.

## Tests couverts

Cas : contrat CSV (21 features, colonnes, types, bornes, `TotalCharges`, lignes vides,
limite de lignes), message de file et clé d'idempotence, classification HTTP permanent
vs transitoire (dont timeout), dispatcher (acceptation/rejet), worker (succès, erreur
permanente, erreur transitoire, doublon), et `/api/recent` (limite 20 + CORS).

## Hypothèses à confirmer par l'équipe

- `customerID` est obligatoire dans le CSV pour rattacher chaque prédiction au client.
- Colonnes supplémentaires rejetées (cohérent avec `extra="forbid"` de l'API).
- Cosmos DB Free Tier choisi en premier ; repli Table Storage si indisponible (#7).
- L'abonnement Event Grid filtré sur `input/` sera créé **après** le déploiement du
  dispatcher (#7), son URL contenant une clé de fonction qui ne doit pas être commitée.

Cette branche est une proposition de code en PR ; elle n'est ni approuvée ni déployée.


## Integration proposal — 26 November

- Both dispatcher and worker conditionally read the expected ETag. If the blob
  was replaced/deleted, the old event is reported as superseded and never scores
  the new bytes. This policy and the version-specific output filename need R2/R1
  review in #14/#21. Use unique filenames for ingestion to avoid superseding uploads.
- A create-only result blob is the canonical record. Concurrent deliveries may both
  call inference, but only one persisted output wins. Cosmos metadata is rebuilt
  from that same output, including after a crash before metadata persistence.
  This is idempotent persistence, not exactly-once execution.
- Cosmos point reads use partition key /fileName. The infrastructure must provision
  that partition key. Table Storage fallback keeps numeric values and sorts timestamps
  (small course demo only; scanning is not a production-scale design).
- Queue sender Base64-encodes JSON for the default Azure Functions queue binding.
  Cloud resources are pre-provisioned by R3; runtime adapters no longer create them.
- API success payload is checked before writes; invalid JSON/schema is retryable.
  CSV rejection messages omit cell values and unexpected header names. Use synthetic
  filenames and inputs in evidence. A reason blob is still keyed by filename, so a later
  rejection can replace an earlier reason; output results are version-specific.
- CI: .github/workflows/ci-pipeline.yml runs offline tests on PR changes.
  Real Azure SDK/binding behavior and poison queue require separate E2E proof.
- This is not a deployed service. The SDK adapters use Azure endpoints and managed
  identity; the offline tests use in-memory adapters, not an actual Azurite instance.
