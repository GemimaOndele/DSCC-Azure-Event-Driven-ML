# Provenance et licence — données d'entraînement (PR #18)

## 1. Ce qui a changé après la revue d'intégration

À la demande d'Aminata (`yayeaminata12`), **aucune donnée source ni jeu de test n'est plus redistribué** dans ce dépôt public :

- `Customer_Churn_Dataset.xlsx` a été **retiré** du dépôt ;
- `model/test_split.csv` a été **retiré** du dépôt et est désormais généré localement, puis ignoré par Git (voir `.gitignore`) ;
- `model/prepare_data.py` **télécharge le classeur source avec une empreinte SHA-256 épinglée** et produit `data/processed/churn_dataset.csv` (également ignoré) ;
- `model/train.py` appelle `ensure_dataset()` : une vérification ou un réentraînement reproductible ne dépend plus d'un fichier versionné, mais d'une récupération documentée et vérifiée.

Le contrat d'entrées `model/features.json` (21 features), le modèle ONNX partagé avec la PR #17 (blob Git `2fc9e022b7029f293bdc3a471f68a91f4d7e57ec`) et les métriques restent inchangés : **aucune valeur de feature n'a été modifiée**, donc pas de rupture de compatibilité avec l'API.

## 2. Source réellement utilisée et filiation

Le classeur précédemment commité n'était **pas une copie du CSV IBM brut**. Une comparaison valeur à valeur a montré qu'il est identique (7 043 lignes × 23 colonnes, toutes les cellules concordantes) au classeur du cas DSCC/PwC-Forage :

- source : [`reports/Task 2 - Customer Retention/02 Churn-Dataset.xlsx`](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/reports/Task%202%20-%20Customer%20Retention/02%20Churn-Dataset.xlsx), feuille `01 Churn-Dataset` ;
- URL de téléchargement épinglée dans `model/prepare_data.py` ;
- SHA-256 du classeur source : `0f71b4ffadf837b37ad6a8747a2abdbb1b5e9db49d6e5847709ec8af01218760` (790 467 octets) ;
- le script vérifie cette empreinte avant toute lecture et refuse un fichier divergent.

Ce classeur lui-même dérive du jeu public **IBM Telco Customer Churn** (`data/Telco-Customer-Churn.csv`, [dépôt IBM officiel](https://github.com/IBM/telco-customer-churn-on-icp4d), licence Apache-2.0 du dépôt, [SHA-256 de référence](https://github.com/Omkar210404/Customer-Churn-Prediction/blob/main/data/README.md) `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`). Les 21 colonnes IBM sont identiques valeur à valeur ; seules deux colonnes s'ajoutent dans la variante DSCC.

## 3. Les deux colonnes ajoutées — origine et justification métier

`numAdminTickets` et `numTechTickets` **ne figurent pas** dans le CSV IBM. Elles proviennent du classeur du cas DSCC/PwC-Forage : elles sont donc **externes à IBM et fournies telles quelles par le matériel de cas**, et non fabriquées par ce dépôt.

| Colonne | Signification métier documentée par le cas | Disponibilité au moment de l'inférence |
|---|---|---|
| `numAdminTickets` | Nombre de tickets administratifs (facturation, contrat, données client) enregistrés dans le dossier client au moment de l'instantané du cas. | Compteur opérationnel issu du système de support, disponible avant la décision de résiliation ; il n'est pas calculé à partir de `Churn`. |
| `numTechTickets` | Nombre de tickets techniques (panne, internet, équipement) enregistrés dans le même dossier client. | Idem : historique de support antérieur au résultat `Churn`, transmis comme feature au moment du scoring. |

**Précision importante sur la fuite temporelle :** ce dépôt ne construit pas ces compteurs et ne lit jamais `Churn` pour les produire (`model/prepare_data.py` ne touche pas à la cible). Le jeu de cas est un instantané unique : l'ordre temporel exact des tickets par rapport à la date de résiliation est une propriété du matériel source, que ce dépôt ne peut pas certifier. Par conséquent :

- ces variables sont traitées comme des compteurs de support **déjà disponibles au scoring** pour la démonstration pédagogique du projet ;
- elles ne doivent pas être présentées comme une preuve de causalité ni réutilisées telles quelles en production sans validation du propriétaire du cas ;
- toute nouvelle génération synthétique devra être faite **sans lire `Churn`** et coordonnée avec `model/features.json`, la PR #17 et l'artefact ONNX partagé.

Aucune affirmation de licence nouvelle n'est faite ici.

## 4. Licence et conditions de redistribution

- Le dépôt du cas indique dans son `NOTICE.md` que **les classeurs et matériaux de cas ne sont pas couverts par la licence MIT du dépôt** et restent soumis aux droits de leurs propriétaires (PwC / Forage). Leur présence n'accorde pas de permission de réutilisation ou de redistribution.
- En conséquence, ce dépôt **ne redistribue plus ces fichiers** : ils sont récupérés à l'exécution depuis leur source publique, avec vérification d'empreinte, uniquement pour le besoin pédagogique du projet DSCC. Toute réutilisation hors de ce cadre doit obtenir l'autorisation du propriétaire du cas.
- Pour les 21 colonnes d'origine, la source amont IBM est publiée sous **Apache-2.0** ; conserver l'attribution IBM si le CSV est téléchargé depuis cette source. La fiche Kaggle `blastchar/telco-customer-churn` indique « Data files © Original Authors ».
- Le jeu ne contient aucune donnée personnelle réelle, aucun secret ni identifiant Azure.
- L'empreinte du classeur source et celle du CSV IBM doivent être revérifiées avant toute mise à jour de `model/prepare_data.py`.

## 5. Tests et preuves

- `model/tests/test_training.py` vérifie la conformité des 23 colonnes au contrat, les métriques de référence, la validité de l'ONNX partagé, le split généré, et la reproductibilité (deux réentraînements isolés comparés octet pour octet pour le split, avec tolérance uniquement sur le dernier chiffre flottant de `onnx_max_probability_error`).
- Le workflow `.github/workflows/ci-ml.yml` exécute ces tests sur la PR #18 ; le téléchargement vérifié par SHA-256 y est disponible.
- Le jeu de test du rapport est généré localement dans `model/test_split.csv` (1 409 lignes, 374 churners) et n'est plus commité.
