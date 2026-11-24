# Provenance et licence — `Customer_Churn_Dataset.xlsx`

## Identification du fichier versionné

- Taille : **794 058 octets** (~775 KiB), une seule feuille `01 Churn-Dataset`.
- Contenu : **7 043 lignes × 23 colonnes** = `customerID` + **21 features** + cible `Churn`.
- Classe positive `Churn = "Yes"` : **1 869 lignes** (26,5 %).
- `TotalCharges` contient **11 cellules vides** : `pd.to_numeric(errors="coerce")` les convertit en `NaN`, puis l'imputation médiane est apprise sur le split d'entraînement à l'intérieur du pipeline (aucune fuite vers le test).
- Métadonnées du classeur (openpyxl) : créé le 2021-04-23, auteur `openpyxl`; aucune donnée Azure, aucun secret.

## Provenance

- Jeu de référence : **IBM Telco Customer Churn** (« fictional telco company », 7 043 clients de Californie, Q3), cité dans l'issue #4 et dans le contrat #14.
- Redistribution publique de référence : [Kaggle — blastchar/telco-customer-churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn). Page de données IBM : [IBM Community — Telco Churn](https://community.ibm.com/community/user/businessanalytics/blogs/steven-macko/2019/07/11/telco-customer-churn-1113).
- Le classeur commité est la **version de travail du projet DSCC** : les colonnes `numAdminTickets` et `numTechTickets` s'ajoutent aux 21 colonnes du CSV public. C'est bien ces deux colonnes, et non un oubli, qui portent le total à 21 features après retrait de `customerID` et `Churn`.

## Licence et conditions d'usage

- La fiche Kaggle indique **« Data files © Original Authors »** : les droits restent aux auteurs originaux (IBM). **Aucune licence OSS (MIT, CC0, Apache…) n'est revendiquée ici.**
- Usage retenu : **usage pédagogique et de démonstration** dans le cadre du projet DSCC, sur des données fictives. Le fichier ne contient ni donnée personnelle réelle ni identifiant Azure.
- Taille conforme à la limite ≤ 50 Mo de l'issue #4. Toute redistribution plus large ou publication hors du dépôt doit être confirmée par l'équipe enseignante : l'issue #4 reste ouverte jusqu'à l'acceptation et à la fusion.
