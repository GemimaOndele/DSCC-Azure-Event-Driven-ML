# Preuve d'entraînement — modèle `1.1.0` (PR #18, 27/11/2026)

Ce document remplace la version `1.0.0` après la décision du 27/11/2026 :
`numAdminTickets` et `numTechTickets` sont retirés car leur disponibilité avant
`Churn` n'est pas documentée dans le classeur du cas. Le modèle livré utilise
**19 entrées** ; le modèle `1.0.0` (21 entrées) n'est conservé que comme
preuve historique/ablation (`model/FEATURE_RISK_ANALYSIS.md`).

## 1. Protocole reproductible

Environnement local : **Python 3.12.10**, dépendances figées dans
`model/requirements.txt` (pandas 2.2.3, numpy 1.26.4, scikit-learn 1.5.2,
joblib, openpyxl 3.1.5, scipy, onnx 1.17.0, onnxruntime 1.20.1, skl2onnx 1.18.0).

```bash
py -3.12 -m pip install -r model/requirements.txt
py -3.12 model/prepare_data.py   # téléchargement vérifié (SHA-256), données non commitées
py -3.12 model/train.py          # écrit model-1.1.0.{joblib,onnx}, metrics.json, test_split.csv
py -3.12 -m pytest model/tests -q
```

`model/prepare_data.py` récupère le classeur du cas DSCC depuis sa source
publique avec une empreinte SHA-256 épinglée et écrit
`data/processed/churn_dataset.csv` (ignoré par Git). Ni le classeur ni
`model/test_split.csv` ne sont redistribués : voir `model/DATASET.md` pour la
provenance, le périmètre d'utilisation et le statut des deux compteurs retirés.

`model/train.py` lit `model/features.json` comme **source unique de vérité**.
Le classeur source conserve ses 23 colonnes ; les deux compteurs sont exclus
explicitement (`EXCLUDED_FROM_MODEL`), les 19 colonnes restantes doivent
correspondre exactement au contrat. Le même fichier est utilisé par l'API
(`feat/ml-api`, PR #17) : la sélection 19/21 est ainsi tranchée côté code dans
les deux lots.

Le job `training-tests` de `.github/workflows/ci-ml.yml` vérifie depuis un
checkout propre : (a) Ruff, (b) les quatre tests hors téléchargement, (c) la
suite complète uniquement si `DATASET_USE_APPROVED == 'true'`. Tant que cette
variable est absente, le CI ne télécharge pas le classeur.

## 2. Les 19 entrées livrées (issues #2 / #4 / #14 / #17 / #18)

`gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`,
`MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`,
`DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`,
`Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`,
`TotalCharges`.

- **`customerID`** sert uniquement d'identifiant client renvoyé par l'API ; il
  n'entre **jamais** dans le modèle.
- **`Churn`** est la cible ; il n'est **jamais** envoyé à l'API.
- **`numAdminTickets` / `numTechTickets`** existent dans le classeur mais sont
  exclus du modèle et du contrat API (`extra='forbid'` côté Pydantic).
- `TotalCharges` est optionnel côté API (`null` ≡ cellule vide) ; le pipeline
  le convertit en numérique puis l'impute par la médiane du train.
- Types, catégories et plages : `model/features.json`.

## 3. Hypothèses statistiques

| Hypothèse | Décision | Justification |
|---|---|---|
| Split | 80/20 **stratifié** sur `Churn`, `random_state=42` | 1 409 lignes de test, proportion de churners conservée |
| Fuites de données | `customerID`, `Churn` et les deux compteurs retirés avant le split ; imputation/standardisation/encodage **appris sur train uniquement** | pipeline sklearn complet, pas de statistiques calculées sur le test |
| Valeurs manquantes | médiane pour les 6 colonnes numériques ; `OneHotEncoder(handle_unknown="ignore")` pour les 13 catégorielles | 11 `TotalCharges` vides ; catégories inédites supportées en inférence |
| Modèle | régression logistique, `class_weight="balanced"`, `max_iter=1000`, graine 42 | modèle léger, classe minoritaire à 26,5 % |
| Seuil de décision | **0,5** (issu du contrat #14), conservé | prédiction `Yes` si `p >= 0,5` dans l'API et dans l'export ONNX |
| Baseline | `DummyClassifier(strategy="most_frequent")` | comparaison minimale exigée par l'issue #4 |

## 4. Résultats `1.1.0` (27/11/2026)

| Métrique | Modèle `1.1.0` | Baseline `most_frequent` | Ancien `1.0.0` (référence historique) |
|---|---:|---:|---:|
| ROC-AUC | **0,8413** | 0,5000 | 0,9273 |
| F1 | **0,6136** | 0,0000 | 0,7328 |
| Accuracy | **0,7381** | 0,7346 | 0,8318 |

Matrice de confusion sur 1 409 lignes : `[[747, 288], [81, 293]]`. Écart
maximal entre probabilités sklearn et ONNX : **1,49e-07** (`np.allclose`,
`rtol=1e-4`, `atol=1e-5` vérifié par `train.py`). Valeurs exactes dans
`model/metrics.json`. L'accuracy du modèle livré est proche de la baseline :
le rapport doit le présenter comme une démonstration pédagogique, pas comme
un résultat production.

## 5. Latence CPU (critère de l'issue #4)

`model/benchmark_cpu.py` mesure l'exécution ONNX seule
(`onnxruntime.CPUExecutionProvider`) sur des lignes synthétiques construites
depuis `model/features.json` : aucun téléchargement du classeur, aucune donnée
client, aucun artefact publié.

```bash
py -3.12 model/benchmark_cpu.py --rows 1 --iterations 50 --warmup 5
py -3.12 model/benchmark_cpu.py --rows 100 --iterations 20 --warmup 5
```

Mesures locales du 28/11/2026 (Python 3.12.10, onnxruntime 1.20.1, Windows 11,
Intel64, ONNX `1.1.0` blob `09ee933f16731e7218189d19d7c3ab98162de34e`) :

| Lignes par appel | Appels chronométrés | Moyenne | p95 | Max | Critère < 1 s |
|---:|---:|---:|---:|---:|---|
| 1 | 50 | 0,065 ms | 0,070 ms | 0,093 ms | respecté |
| 100 | 20 | 0,190 ms | 0,203 ms | 0,218 ms | respecté |

Ces valeurs dépendent de la machine et couvrent **uniquement l'inférence CPU
du modèle** : ni HTTP/validation Pydantic (#17), ni queue/Functions (#21), ni
Azure. La latence `inference_latency_ms` exposée par l'API et les gardes
d'alerte de #20 restent la mesure d'intégration ; ce benchmark apporte la
preuve modèle reproductible demandée par l'issue #4. Aucun seuil d'alerte ni
déploiement n'est revendiqué ici.

## 6. Reproductibilité et preuves

- `py -3.12 -m pytest model/tests -q` exécute 8 tests : conformité du classeur
  au contrat 19 features, valeurs de référence des métriques, validité ONNX +
  **empreinte Git partagée `09ee933f16731e7218189d19d7c3ab98162de34e`**,
  jeu de test, ré-entraînement complet dans un dossier temporaire avec
  comparaison structurée de `metrics.json` (sauf `onnx_max_probability_error`,
  toléré à `1e-5`) et comparaison octet pour octet de `test_split.csv`,
  non-redistribution des données et retrait des anciens binaires `1.0.0`,
  téléchargement depuis un dossier vide avec contrôle SHA-256, rejet d'une
  source altérée.
- Exécution locale du 27/11/2026 sur le classeur épinglé : **8 passed** ;
  `ruff check model` vert. Le run CI officiel sur la nouvelle tête reste à
  consigner après push ; les runs `45885194571` et antérieurs portaient sur
  `1.0.0`.
- `model/model-1.1.0.onnx` est le blob partagé avec la PR #17. L'export est
  regénéré à chaque entraînement mais la structure et les probabilités sont
  identiques ; c'est le fichier commité qui fait foi pour les deux PR.
- Jeu de test pour le rapport : **`model/test_split.csv`**, généré localement
  (1 409 lignes, `customerID` et `Churn` réattachés pour la lecture, 374
  churners) puis ignoré par Git. Il s'agit exactement du split utilisé pour
  les métriques ci-dessus.
- Documentation du dataset : `model/DATASET.md` (source épinglée,
  non-redistribution, licence IBM Apache-2.0 limitée aux colonnes d'origine,
  droits du cas non établis, décision 19 features).

## 7. État

Le modèle est **en PR, pas dans `main`** ; l'issue #4 reste ouverte jusqu'aux
vérifications d'acceptation, à l'approbation GitHub et à la fusion. Le passage
à `1.1.0` doit être validé avec le contrat #14, l'API #17, le worker #21 et la
CI #23 avant intégration. Cette note n'est pas une approbation.
