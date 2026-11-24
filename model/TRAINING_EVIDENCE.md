# Preuve d'entraînement — modèle `1.0.0` (PR #18)

Ce document répond à la note d'audit du 24/11/2026 : liste des 21 entrées, hypothèses statistiques, reproductibilité, métriques et jeu de test utile au rapport.

## 1. Protocole reproductible

Environnement local : **Python 3.12.10**, dépendances figées dans `model/requirements.txt` (pandas 2.2.3, numpy 1.26.4, scikit-learn 1.5.2, joblib 1.4.2, openpyxl 3.1.5, scipy 1.14.1, onnx 1.17.0, onnxruntime 1.20.1, skl2onnx 1.18.0).

```bash
py -3.12 -m pip install -r model/requirements.txt
py -3.12 model/prepare_data.py   # téléchargement vérifié (SHA-256), données non commitées
py -3.12 model/train.py
py -3.12 -m pytest model/tests -q
```

`model/prepare_data.py` récupère le classeur du cas DSCC depuis sa source publique avec une empreinte SHA-256 épinglée et écrit `data/processed/churn_dataset.csv` (ignoré par Git). Ni le classeur ni `model/test_split.csv` ne sont redistribués : voir `model/DATASET.md` pour la provenance, le périmètre d'utilisation et le statut temporel des deux compteurs de tickets. `model/train.py` appelle `ensure_dataset()` automatiquement.

Le job `training-tests` de `.github/workflows/ci-ml.yml` applique explicitement le même protocole depuis un checkout propre : (a) vérification qu'aucun `data/`, classeur source ou split n'est versionné ou déjà présent, (b) `python model/prepare_data.py` (téléchargement vérifié par SHA-256 puis préparation), (c) `python -m pytest model/tests -q`. Les tests incluent un scénario « environnement propre » qui force le téléchargement dans un dossier temporaire sans fichier local, et un scénario de refus d'une empreinte divergente : le CI ne dépend donc d'aucun artefact préexistant.

`model/train.py` lit `model/features.json` comme **source unique de vérité** et échoue si les colonnes du dataset ne correspondent pas exactement aux 21 features attendues. Le même fichier est utilisé par l'API (`feat/ml-api`, PR #17) : les 19 vs 21 entrées du contrat #14 sont ainsi tranchées côté code.

## 2. Les 21 entrées confirmées (issue #4 / #14 / #17)

`gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`, `numAdminTickets`, `numTechTickets`.

- **`customerID`** sert uniquement d'identifiant client renvoyé par l'API ; il n'entre **jamais** dans le modèle.
- **`Churn`** est la cible ; il n'est **jamais** envoyé à l'API.
- Les types, valeurs autorisées et plages sont dans `model/features.json` et sont validés par Pydantic dans l'API (champs inconnus ou catégories inconnues → 422).
- `TotalCharges` est optionnel côté API (`null` ≡ cellule vide) ; le pipeline le convertit en numérique puis l'impute par la médiane du train.

## 3. Hypothèses statistiques

| Hypothèse | Décision | Justification |
|---|---|---|
| Split | 80/20 **stratifié** sur `Churn`, `random_state=42` | 1 409 lignes de test, proportion de churners conservée |
| Fuites de données | `customerID` et `Churn` retirés avant le split ; imputation/standardisation/encodage **appris sur train uniquement** | pipeline sklearn complet, pas de statistiques calculées sur le test |
| Validité temporelle des compteurs | `numAdminTickets` / `numTechTickets` fournis par le classeur du cas ; **disponibilité avant `Churn` non démontrée** | instantané sans horodatage des tickets ; usage pédagogique DSCC uniquement, décision d'équipe requise avant production (`model/DATASET.md` §3) |
| Valeurs manquantes | médiane pour les 6 colonnes numériques ; `OneHotEncoder(handle_unknown="ignore")` pour les 15 catégorielles | 11 `TotalCharges` vides ; catégories inédites supportées en inférence |
| Modèle | régression logistique, `class_weight="balanced"`, `max_iter=1000`, graine 42 | modèle léger, classe minoritaire à 26,5 % |
| Seuil de décision | **0,5** (issu du contrat #14), conservé après lecture de la courbe de probabilités sur le test | prédiction `Yes` si `p >= 0,5` dans l'API et dans l'export ONNX |
| Baseline | `DummyClassifier(strategy="most_frequent")` | comparaison minimale exigée par l'issue #4 |

## 4. Résultats (inchangés par la correction)

| Métrique | Modèle | Baseline `most_frequent` |
|---|---|---|
| ROC-AUC | **0.9273** | 0.5000 |
| F1 | **0.7328** | 0.0000 |
| Accuracy | **0.8318** | 0.7346 |

Matrice de confusion sur 1 409 lignes : `[[847, 188], [49, 325]]`. Écart maximal entre probabilités sklearn et ONNX : **2,23e-07** (`np.allclose`, `rtol=1e-4`, `atol=1e-5` vérifié par `train.py`). Valeurs exactes dans `model/metrics.json`.

## 5. Reproductibilité et preuves

- `py -3.12 -m pytest model/tests -q` exécute 8 tests : conformité du dataset aux 21 features, valeurs de référence des métriques, validité ONNX + **empreinte Git partagée `2fc9e022b7029f293bdc3a471f68a91f4d7e57ec`**, jeu de test, et **ré-entraînement complet dans un dossier temporaire** avec comparaison exacte de toutes les valeurs de `metrics.json` (sauf l'écart ONNX flottant, toléré à `1e-5` car ses derniers chiffres dépendent de la plateforme) et comparaison octet pour octet de `test_split.csv`. Les trois tests ajoutés après la relecture du 24/11/2026 vérifient l'absence de données versionnées, le téléchargement + contrôle SHA-256 + préparation depuis un dossier vide, et le rejet d'une source altérée.
- Exécution locale du 24/11/2026 : **8 passed**. CI : workflow `.github/workflows/ci-ml.yml`, job `training-tests`, sur la PR #18 (Python 3.12 + dépendances figées, préparation explicite avant les tests).
- Le blob ONNX commité n'a pas été réécrit : l'export régénéré a la même structure et les mêmes probabilités, mais un ordre de sérialisation des attributs différent (SHA Git `d130e3be…` en local). C'est pourquoi l'artefact partagé avec la PR #17 est conservé tel quel. Aucune valeur de feature n'ayant changé, la compatibilité avec l'API #17 est préservée.
- Jeu de test pour le rapport : **`model/test_split.csv`**, généré localement (1 409 lignes, `customerID` et `Churn` réattachés pour la lecture, 374 churners) puis ignoré par Git. Il s'agit exactement du split utilisé pour les métriques ci-dessus.
- Documentation du dataset : `model/DATASET.md` (source du cas vérifiée par SHA-256, non-redistribution, périmètre pédagogique DSCC confirmé sans revendication de sous-licence, origine externe des compteurs `numAdminTickets`/`numTechTickets` et **statut temporel non démontré**, licence IBM Apache-2.0 limitée aux colonnes d'origine et droits du cas pour la variante DSCC).

## 6. État

Le modèle est **en PR, pas dans `main`** ; l'issue #4 reste ouverte jusqu'aux vérifications d'acceptation, à l'approbation GitHub et à la fusion. Cette note n'est pas une approbation.
