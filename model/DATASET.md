# Provenance et licence — données d'entraînement (PR #18)

## 1. Ce qui a changé après la revue d'intégration

À la demande d'Aminata (`yayeaminata12`), **aucune donnée source ni jeu de test n'est plus redistribué** dans ce dépôt public :

- `Customer_Churn_Dataset.xlsx` a été **retiré** du dépôt ;
- `model/test_split.csv` a été **retiré** du dépôt et est désormais généré localement, puis ignoré par Git (voir `.gitignore`) ;
- `model/prepare_data.py` **télécharge le classeur source avec une empreinte SHA-256 épinglée** et produit `data/processed/churn_dataset.csv` (également ignoré) ;
- `model/train.py` appelle `ensure_dataset()` : une vérification ou un réentraînement reproductible ne dépend plus d'un fichier versionné, mais d'une récupération documentée et vérifiée ;
- le job `training-tests` de `.github/workflows/ci-ml.yml` part d'un checkout propre, vérifie l'absence de fichier local préexistant, exécute explicitement `python model/prepare_data.py` (téléchargement + vérification SHA-256 + préparation), puis lance les tests (voir §5).

Le contrat d'entrées `model/features.json` (21 features), le modèle ONNX partagé avec la PR #17 (blob Git `2fc9e022b7029f293bdc3a471f68a91f4d7e57ec`) et les métriques restent inchangés : **aucune valeur de feature n'a été modifiée**, donc pas de rupture de compatibilité avec l'API. Le point temporel soulevé par la revue est traité au §3 ; sa décision finale est explicitement laissée à l'équipe, car retirer ces colonnes casserait ce contrat partagé.

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
- **Périmètre actuel :** les compteurs sont utilisés tels quels pour la démonstration pédagogique DSCC uniquement. Ils ne doivent être présentés ni comme une preuve de causalité, ni comme une feature validée pour la production, ni comme un signal disponible avant le churn en environnement réel.
- **Décision à trancher par l'équipe avant toute production :** conserver les colonnes avec la réserve ci-dessus, ou les retirer. Le retrait nécessite une coordination explicite : réentraînement, mise à jour de `model/features.json` (19 features), remplacement de l'artefact ONNX partagé, mise à jour de la PR #17/API et des métriques/preuves. **Aucun retrait n'est appliqué dans ce commit** : le changement silence le contrat partagé #17/#18 sans accord d'équipe. La question reste ouverte pour la revue de la PR #18 et le propriétaire du cas. Une ablation reproductible (21 vs 19 features, même graine et même split) chiffre l'impact de ces deux colonnes dans [`model/FEATURE_RISK_ANALYSIS.md`](FEATURE_RISK_ANALYSIS.md).

## 4. Licence, conditions d'utilisation et périmètre exact

- Le [`NOTICE.md` du dépôt source](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/NOTICE.md) déclare que la licence MIT ne s'applique qu'au code et à la documentation créés par l'auteur. Il exclut nommément les classeurs de `reports/Task 2 - Customer Retention/`, les fichiers PBIX et les captures de référence, qui **restent soumis aux droits de leurs propriétaires** (PwC / Forage). Le dépôt source précise que leur présence n'accorde **aucune** permission de réutilisation, de redistribution ou de sous-licence, et qu'il n'est ni commissionné ni approuvé par PwC.
- **Confirmation explicite demandée par la revue :** le téléchargement et l'utilisation automatisés du classeur par `model/prepare_data.py` sont **limités au cadre pédagogique du projet DSCC**, seul cadre dans lequel ce matériel de cas est utilisé ici. Ils consistent en une récupération à l'exécution depuis l'URL publique de la source, suivie d'une vérification SHA-256 et d'une conversion locale dans un fichier ignoré par Git. **Aucun classeur, extrait ou dérivé n'est republié** dans ce dépôt, dans une image conteneur ou dans un artefact ; nous ne revendiquons aucun droit de redistribution ni de sous-licence. Nous ne prétendons pas non plus que la source accorde une licence positive d'au-delà de ce périmètre : notre usage reste dans les limites déclarées par la source et toute réutilisation **hors du cadre pédagogique DSCC** (production, publication du classeur ou d'un dérivé, redistribution) nécessite l'autorisation du propriétaire du cas (PwC / Forage).
- **La licence Apache-2.0 du dépôt IBM ne couvre pas le classeur PwC/Forage dérivé**, ni les deux colonnes ajoutées. Elle ne s'applique qu'aux 21 colonnes d'origine lorsqu'elles sont obtenues depuis le dépôt IBM officiel ; conserver alors l'attribution IBM. La mention Kaggle « Data files © Original Authors » ne constitue pas non plus une autorisation de republier le classeur modifié.
- Le jeu ne contient aucune donnée personnelle réelle, aucun secret ni identifiant Azure.
- L'empreinte du classeur source et celle du CSV IBM doivent être revérifiées avant toute mise à jour de `model/prepare_data.py`.

## 5. Tests et preuves (environnement propre)

- `model/tests/test_training.py` vérifie (1) la conformité des 23 colonnes au contrat de 21 features, (2) les métriques de référence, (3) la validité et l'empreinte Git de l'ONNX partagé, (4) le split généré, (5) la reproductibilité (deux réentraînements isolés comparés de manière structurée, avec tolérance uniquement sur le dernier chiffre flottant de `onnx_max_probability_error`, et `test_split.csv` comparé octet pour octet), (6) qu'aucun jeu de données n'est versionné dans Git, (7) qu'un environnement sans fichier local télécharge bien la source épinglée, en vérifie le SHA-256 et produit le CSV (8) qu'une source altérée est rejetée et supprimée.
- Le workflow `.github/workflows/ci-ml.yml`, job `training-tests`, exécute sur un checkout **propre** : vérification qu'aucun `data/`, `Customer_Churn_Dataset.xlsx` ou `model/test_split.csv` n'est versionné ou présent localement, puis `python model/prepare_data.py` (téléchargement depuis l'URL épinglée, refus d'une empreinte divergente, préparation de `data/processed/churn_dataset.csv`), puis `python -m pytest model/tests -q`. Les tests ne dépendent donc d'aucun fichier préexistant sur la machine d'exécution.
- Le jeu de test du rapport est généré localement dans `model/test_split.csv` (1 409 lignes, 374 churners) et n'est plus commité ; le CSV préparé est ignoré par Git (`data/`).
- Ces preuves couvrent la **reproductibilité**, pas la **validité temporelle** des compteurs (§3), qui reste une décision d'équipe avant production.
