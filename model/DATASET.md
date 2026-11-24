# Provenance et licence — `Customer_Churn_Dataset.xlsx`

## Identification du fichier versionné

- Taille : **794 058 octets** (~775 KiB), une seule feuille `01 Churn-Dataset`.
- Contenu : **7 043 lignes × 23 colonnes** = `customerID` + **21 features** + cible `Churn`.
- Classe positive `Churn = "Yes"` : **1 869 lignes** (26,5 %).
- `TotalCharges` contient **11 cellules vides** : `pd.to_numeric(errors="coerce")` les convertit en `NaN`, puis l'imputation médiane est apprise sur le split d'entraînement à l'intérieur du pipeline (aucune fuite vers le test).
- Métadonnées du classeur (openpyxl) : créé le 2021-04-23, auteur `openpyxl`; aucune donnée Azure, aucun secret.

## Provenance

### Source IBM officielle identifiée (revue complémentaire, 24/11/2026)

- Dépôt IBM : [IBM/telco-customer-churn-on-icp4d](https://github.com/IBM/telco-customer-churn-on-icp4d)
- Données source publiées par IBM : [`data/Telco-Customer-Churn.csv`](https://github.com/IBM/telco-customer-churn-on-icp4d/tree/master/data)
- Licence du dépôt officiel : [Apache-2.0](https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/LICENSE) pour le dépôt. **Attention :** la licence Apache-2.0 couvre le dépôt tel que publié ; elle ne doit pas être interprétée automatiquement comme accordant tous les droits sur un classeur modifié/redistribué sans vérifier l'absence d'exceptions ou de droits tiers sur les données elles-mêmes.
- Redistribution publique de référence : [Kaggle — blastchar/telco-customer-churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn). Page de données IBM : [IBM Community — Telco Churn](https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113).
- Jeu de référence : **IBM Telco Customer Churn** (« fictional telco company », 7 043 clients de Californie, Q3), cité dans l'issue #4 et dans le contrat #14.

### Filiation vérifiée avec le fichier IBM

Contrôle effectué le 24/11/2026 en comparant `Customer_Churn_Dataset.xlsx` (`01 Churn-Dataset`) au CSV IBM `Telco-Customer-Churn.csv` :

| Contrôle | Résultat |
|---|---|
| Nombre de lignes | 7 043 vs 7 043 — identique |
| Ordre des `customerID` | Identique ligne à ligne |
| Colonnes communes IBM (21) | Identiques valeur à valeur après normalisation triviale des espaces/vides `TotalCharges` |
| Colonnes supplémentaires DSCC | `numAdminTickets`, `numTechTickets` (absentes du CSV IBM) |

Conclusion : `Customer_Churn_Dataset.xlsx` est **traçable comme dérivation du fichier IBM** sur les 21 colonnes d'origine. La dérivation n'est cependant **pas entièrement justifiée** tant que l'origine des deux colonnes ajoutées n'est pas documentée.

## Colonnes ajoutées `numAdminTickets` / `numTechTickets` — point bloquant

Ces deux colonnes portent le total à 21 features modèle (après retrait de `customerID` et `Churn`) et font partie du contrat partagé `model/features.json` / PR #17.

**État actuel (à compléter avant fusion de #18) :**

- **Source / méthode de génération :** non documentée dans l'historique du dépôt. L'auteur de la dérivation doit préciser si ces colonnes proviennent d'une source autorisée, d'un calcul déterministe, ou d'une génération synthétique.
- **Graine / reproductibilité :** si synthétiques, fournir le script/générateur, la graine, les paramètres et la version des dépendances permettant de reproduire exactement les valeurs.
- **Date de disponibilité par rapport à `Churn` :** à justifier explicitement. Les compteurs de tickets doivent représenter une information disponible au moment de la prédiction, pas une information postérieure ou dérivée de l'issue `Churn`.
- **Vérification rapide effectuée (non suffisante pour lever le blocage) :** les colonnes sont entières, bornées (`numAdminTickets` 0–5, `numTechTickets` 0–9), avec forte masse à 0 ; moyenne `numTechTickets` plus élevée pour `Churn=Yes` (1,16) que `Churn=No` (0,15). Cette corrélation n'est pas une preuve de fuite, mais elle impose de documenter le protocole de fabrication.

**Pour lever la demande de corrections :** soit prouver la filiation complète et documenter la fabrication/légitimité de redistribution des deux colonnes, soit remplacer le fichier versionné par une préparation reproductible depuis une source autorisée et documentée, en générant les éventuelles colonnes synthétiques sans fuite temporelle. Dans le second cas, mettre à jour tests/artefacts/README et coordonner le modèle ONNX partagé avec `feat(ml-api)` / PR #17, sans casser silencieusement la compatibilité du modèle déjà revu.

## Licence et conditions d'usage

- Le dépôt IBM source est publié sous **Apache-2.0** ; le fichier `Telco-Customer-Churn.csv` est distribué dans ce dépôt. La fiche Kaggle indique **« Data files © Original Authors »**. **Aucune nouvelle licence ni approbation n'est accordée par ce message.**
- Avant toute fusion/redistribution élargie, l'équipe doit confirmer les droits applicables au fichier DSCC dérivé (données IBM + colonnes ajoutées) et conserver les attributions/mentions requises.
- Usage retenu : **usage pédagogique et de démonstration** dans le cadre du projet DSCC, sur des données fictives. Le fichier ne contient ni donnée personnelle réelle ni identifiant Azure.
- Taille conforme à la limite ≤ 50 Mo de l'issue #4. Ne pas fusionner #18 avant clarification de provenance/licence et CI vert.
