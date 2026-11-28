# Provenance et licence — données d'entraînement (PR #18)

## 1. Ce qui a changé après la revue d'intégration

À la demande d'Aminata (`yayeaminata12`), **aucun fichier de données source ni jeu de test n'est présent dans l'arbre courant** de cette branche (la suppression de l'arbre courant n'efface pas l'historique Git) :

- `Customer_Churn_Dataset.xlsx` a été **retiré** du dépôt ;
- `model/test_split.csv` a été **retiré** du dépôt et est désormais généré localement, puis ignoré par Git (voir `.gitignore`) ;
- `model/prepare_data.py` **télécharge le classeur source avec une empreinte SHA-256 épinglée** et produit `data/processed/churn_dataset.csv` (également ignoré) ;
- `model/train.py` appelle `ensure_dataset()` : une vérification ou un réentraînement reproductible ne dépend plus d'un fichier versionné, mais d'une récupération documentée et vérifiée ;
- le job `training-tests` exécute désormais les quatre tests hors téléchargement et Ruff ; les quatre tests dépendant du classeur ne sont exécutés que si `DATASET_USE_APPROVED=true` (voir §5).

Suite à la décision du 27/11/2026 (§3), le contrat d'entrées `model/features.json` passe à **19 features** et l'artefact partagé avec la PR #17 devient **`1.1.0`** (blob Git `09ee933f16731e7218189d19d7c3ab98162de34e`). Les anciens binaires `1.0.0` sont retirés de l'arbre courant ; les deux PR sont mises à jour ensemble pour éviter toute divergence d'artefact. Le classeur source reste le même et reste non redistribué.

## 2. Source réellement utilisée et filiation

Le classeur précédemment commité n'était **pas une copie du CSV IBM brut**. Une comparaison valeur à valeur a montré qu'il est identique (7 043 lignes × 23 colonnes, toutes les cellules concordantes) au classeur du cas DSCC/PwC-Forage :

- source : [`reports/Task 2 - Customer Retention/02 Churn-Dataset.xlsx`](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/reports/Task%202%20-%20Customer%20Retention/02%20Churn-Dataset.xlsx), feuille `01 Churn-Dataset` ;
- URL de téléchargement épinglée dans `model/prepare_data.py` ;
- SHA-256 du classeur source : `0f71b4ffadf837b37ad6a8747a2abdbb1b5e9db49d6e5847709ec8af01218760` (790 467 octets, empreinte revérifiée le 24/11/2026 sur l'URL `raw.githubusercontent.com` et sur le blob GitHub `b5b8ca91b064a955ea911e6dd2fce26f54fe4e54`) ;
- le script vérifie cette empreinte avant toute lecture et refuse un fichier divergent.

Ce classeur lui-même dérive du jeu public **IBM Telco Customer Churn** (`data/Telco-Customer-Churn.csv`, [dépôt IBM officiel](https://github.com/IBM/telco-customer-churn-on-icp4d), licence Apache-2.0 du dépôt, [SHA-256 de référence](https://github.com/Omkar210404/Customer-Churn-Prediction/blob/main/data/README.md) `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`). Les 21 colonnes IBM sont identiques valeur à valeur ; seules deux colonnes s'ajoutent dans la variante DSCC. **La licence Apache-2.0 du dépôt IBM couvre ce dépôt IBM et ses colonnes d'origine ; elle ne couvre ni le classeur PwC/Forage dérivé ni les deux colonnes ajoutées** (voir §4).

## 3. Les deux colonnes ajoutées — origine et statut temporel

`numAdminTickets` et `numTechTickets` **ne figurent pas** dans le CSV IBM. Elles proviennent du classeur du cas DSCC/PwC-Forage : elles sont **externes à IBM et fournies telles quelles par le matériel de cas**, et non fabriquées par ce dépôt. Le [README de la tâche 2](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/reports/Task%202%20-%20Customer%20Retention/README.md), le [script de préparation amont](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/scripts/prepare_data.py) et le [fichier de validation des rapports](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/docs/reference/model-data-validation.json) confirment que ces colonnes sont des champs du classeur source, sans documenter leur mode de calcul ni leur horodatage.

| Colonne | Signification métier documentée par le cas | Disponibilité avant `Churn` |
|---|---|---|
| `numAdminTickets` | Nombre de tickets administratifs (facturation, contrat, données client) enregistrés dans le dossier client au moment de l'instantané du cas. | **Non démontrée** : aucun horodatage ni règle de calcul publié dans la source ; voir l'évaluation du risque ci-dessous. |
| `numTechTickets` | Nombre de tickets techniques (panne, internet, équipement) enregistrés dans le même dossier client. | **Non démontrée** : idem. |

**Précision importante sur la fuite temporelle (remplace l'affirmation précédente) :** le jeu de cas est un instantané unique. Ni le README du cas, ni son script de préparation, ni le JSON de validation des rapports ne publient la date d'ouverture des tickets ou la date à laquelle les compteurs ont été agrégés. **Nous ne pouvons donc pas certifier, et nous n'affirmons plus, que ces compteurs étaient disponibles avant la décision de résiliation.** La formulation antérieure (« disponible avant la décision de résiliation » / « historique de support antérieur au résultat `Churn` ») était trop forte au regard des sources consultées et est retirée.

La seule garantie vérifiable ici est négative : ce dépôt ne construit pas ces compteurs et ne lit jamais `Churn` pour les produire (`model/prepare_data.py` ne touche pas à la cible). Les points suivants en découlent :

- **Évaluation du risque de fuite :** si le matériel source a comptabilisé des tickets ouverts après la résiliation, ces deux variables encodent une information postérieure à la cible et peuvent gonfler l'AUC/F1 rapportés. Le risque ne peut être exclu à partir de l'instantané ; il n'est pas compensé par le CI vert, qui ne vérifie que la reproductibilité du pipeline.
- **Décision appliquée le 27/11/2026 :** retrait des deux compteurs du modèle livré. `model/train.py` les exclut explicitement du jeu d'entraînement, `model/features.json` passe à 19 entrées, l'ONNX `1.1.0` remplace `1.0.0` dans #17/#18 et les métriques sont recalculées avec la même graine et le même split. Le classeur source épinglé conserve ses 23 colonnes : seule la sélection de features change.
- **Conséquence pour le rapport :** le modèle `1.1.0` (AUC 0,8413 / F1 0,6136) remplace les chiffres `0,9273 / 0,7328` du modèle `1.0.0`, dont l'AUC était vraisemblablement optimiste si les tickets ont été agrégés après la résiliation. L'ablation reproductible (19 vs 21, même graine et même split) chiffre l'écart dans [`model/FEATURE_RISK_ANALYSIS.md`](FEATURE_RISK_ANALYSIS.md). Le retrait ne prouve pas une fuite ; il supprime une feature dont l'antériorité n'est pas démontrable.
- **Toujours à valider par l'équipe :** le contrat #14, le worker #21, la CI #23 et le tableau de bord #19 doivent refléter 19 entrées et la version `1.1.0`. L'autorisation du classeur et la diffusion de l'artefact dérivé restent distinctes et non établies (§4).

## 4. Licence, conditions d'utilisation et périmètre exact

- Le [`NOTICE.md` du dépôt source](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/NOTICE.md) déclare que la licence MIT ne s'applique qu'au code et à la documentation créés par l'auteur. Il exclut nommément les classeurs de `reports/Task 2 - Customer Retention/`, les fichiers PBIX et les captures de référence, qui **restent soumis aux droits de leurs propriétaires** (PwC / Forage). Le dépôt source précise que leur présence n'accorde **aucune** permission de réutilisation, de redistribution ou de sous-licence, et qu'il n'est ni commissionné ni approuvé par PwC.
- **Autorisation non établie :** le cadre pédagogique DSCC est le périmètre prévu, mais ne constitue pas à lui seul une permission positive de téléchargement automatisé ou d'utilisation du classeur exact. La source publique et son empreinte ne constituent pas une licence. Demander à l'enseignant la source autorisée du TP6 et, si nécessaire, une confirmation du détenteur des droits. Tant que cette confirmation n'est pas consignée, garder `DATASET_USE_APPROVED` désactivé et ne pas télécharger ou réentraîner à nouveau à partir de ce classeur.
- **Artefact entraîné :** l'ONNX `1.1.0` remplace `1.0.0` dans #17/#18. Une image GHCR de branche construite avec l'ancien modèle a été publiée lors du run 45880950088 (SHA 6fb916d) : il serait inexact d'affirmer qu'aucun artefact dérivé n'a jamais été publié. La visibilité du package et les droits de diffusion du nouvel artefact restent à confirmer. Maintenir `MODEL_ARTIFACT_PUBLISH_APPROVED` désactivé tant que la permission applicable n'est pas documentée ; ne pas déployer cette image de branche. L'exécution du modèle avec des lignes synthétiques dans la CI ne constitue pas une autorisation de publication.
- **Historique :** les fichiers de données ont été retirés de l'arbre courant ; leur éventuelle persistance dans des commits historiques, des artefacts ou des copies externes doit être examinée par le propriétaire du dépôt. Ne pas réécrire l'historique, supprimer de package ou changer la visibilité sans décision explicite et plan coordonné.
- **La licence Apache-2.0 du dépôt IBM ne couvre pas le classeur PwC/Forage dérivé**, ni les deux colonnes ajoutées. Elle ne s'applique qu'aux 21 colonnes d'origine lorsqu'elles sont obtenues depuis le dépôt IBM officiel ; conserver alors l'attribution IBM. La mention Kaggle « Data files © Original Authors » ne constitue pas non plus une autorisation de republier le classeur modifié.
- Le jeu ne contient aucune donnée personnelle réelle, aucun secret ni identifiant Azure.
- L'empreinte du classeur source et celle du CSV IBM doivent être revérifiées avant toute mise à jour de `model/prepare_data.py`.
- Un projet de message à l'enseignant puis, si nécessaire, au détenteur des droits est fourni dans [`DATASET_AUTHORIZATION_REQUEST.md`](DATASET_AUTHORIZATION_REQUEST.md). Il n'a pas été envoyé et ne constitue pas une autorisation.

## 5. Tests et preuves (environnement propre)

- `model/tests/test_training.py` vérifie (1) la conformité des 23 colonnes du classeur au contrat de 19 features (les deux compteurs étant exclus), (2) les métriques `1.1.0` de référence, (3) la validité et l'empreinte Git de l'ONNX partagé, (4) le split généré, (5) la reproductibilité (deux réentraînements isolés comparés de manière structurée, avec tolérance uniquement sur le dernier chiffre flottant de `onnx_max_probability_error`, et `test_split.csv` comparé octet pour octet), (6) qu'aucun jeu de données ni ancien binaire `1.0.0` n'est versionné, (7) qu'un environnement sans fichier local télécharge bien la source épinglée, en vérifie le SHA-256 et produit le CSV (8) qu'une source altérée est rejetée et supprimée.
- Historique : huit tests ont réussi sur le modèle `1.0.0`. Le 27/11/2026, après le passage à `1.1.0`, huit tests ont été relancés en local (les quatre tests dépendant du classeur utilisent le fichier épinglé déjà préparé). En CI, les quatre tests hors téléchargement restent seuls exécutés tant que `DATASET_USE_APPROVED != 'true'` ; la suite complète est conditionnée à cette variable.
- Le jeu de test du rapport est généré localement dans `model/test_split.csv` (1 409 lignes, 374 churners) et n'est plus commité ; le CSV préparé est ignoré par Git (`data/`).
- Ces preuves couvrent la **reproductibilité**, pas l'autorisation du classeur ni la **validité temporelle** des compteurs (§3-4).
