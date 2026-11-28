# Projet de demande d'autorisation — classeur du cas DSCC (PR #18)

**Statut : BROUILLON, aucune autorisation reçue à ce jour.** Ce document ne crée
aucun droit et ne doit pas être cité comme une permission. Il prépare la
demande explicite réclamée dans la revue de #18 et dans l'issue #4.

## Faits à faire valider (à ne pas présenter comme une licence)

- Source exacte utilisée par `model/prepare_data.py` :
  [`reports/Task 2 - Customer Retention/02 Churn-Dataset.xlsx`](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/reports/Task%202%20-%20Customer%20Retention/02%20Churn-Dataset.xlsx),
  feuille `01 Churn-Dataset`, URL `raw.githubusercontent.com` épinglée dans le script.
- Empreinte SHA-256 du fichier exact :
  `0f71b4ffadf837b37ad6a8747a2abdbb1b5e9db49d6e5847709ec8af01218760`
  (790 467 octets, 7 043 lignes × 23 colonnes).
- Le [`NOTICE.md`](https://github.com/TimKong21/telecom-customer-operations-decision-hub/blob/main/NOTICE.md)
  du dépôt source exclut nommement les classeurs de `reports/Task 2` de sa
  licence MIT : leur présence publique n'accorde ni réutilisation, ni
  redistribution, ni sous-licence.
- La licence Apache-2.0 du dépôt IBM couvre les 21 colonnes d'origine obtenues
  depuis IBM, **pas** le classeur DSCC dérivé ni les deux colonnes de tickets.
- Le classeur, le CSV préparé et le split de test ne sont pas versionnés dans
  l'arbre courant ; seul l'ONNX dérivé `1.1.0` est commité (blob Git
  `09ee933f16731e7218189d19d7c3ab98162de34e`). Une image GHCR de branche avec
  l'ancien modèle a déjà été publiée (run `45880950088`, commit `6fb916d`) :
  ce point doit être traité séparément.

## Trois autorisations distinctes à demander

1. **Usage pédagogique du classeur exact** pour entraîner, évaluer et
   réentraîner le modèle dans le cadre du projet DSCC ECE Paris.
2. **Récupération automatisée** de cette URL épinglée, y compris depuis la CI
   GitHub Actions, avec vérification SHA-256 et conservation locale temporaire.
3. **Diffusion de l'artefact dérivé** (`model/model-1.1.0.onnx`, image API,
   publication GHCR si elle est envisagée) pour la démonstration et la
   soutenance. Ne pas déduire 3 de 1 ou 2.

## Message proposé à l'enseignant / responsable du TP6

> Objet : Autorisation d'usage du classeur « 02 Churn-Dataset.xlsx » — projet DSCC 2026
>
> Bonjour [nom],
>
> Dans le cadre du projet DSCC (ECE Paris, MSc 2 AI), notre équipe entraîne un
> modèle de churn à partir du classeur utilisé pour le TP 6 « Customer
> Retention », à l'URL [URL exacte de `prepare_data.py`]. Nous avons vérifié son
> empreinte SHA-256 : `0f71b4ff…` (fichier de 790 467 octets). Le `NOTICE.md`
> du dépôt source indiquant que ce classeur reste soumis aux droits de son
> propriétaire, nous ne souhaitons pas présumer d'une autorisation.
>
> Pouvez-vous nous confirmer, par retour d'e-mail :
>
> 1. que ce fichier est bien la source autorisée du TP 6 pour notre usage
>    pédagogique (entraînement, évaluation, réentraînement) ;
> 2. que son téléchargement automatisé depuis cette URL, avec contrôle
>    d'empreinte, est autorisé dans notre pipeline CI ;
> 3. si la diffusion du modèle dérivé (ONNX `1.1.0`) et, le cas échéant, d'une
>    image d'API pour la soutenance est couverte par ce cadre, ou s'il faut
>    demander une autorisation distincte ;
> 4. dans ce dernier cas, le contact du détenteur des droits (PwC / Forage) à
>    qui adresser une demande précise.
>
> Nous consignerons votre réponse dans notre registre de preuves et garderons
> les garde-fous CI désactivés jusqu'à réception. Merci d'avance.
>
> Cordialement, [nom, rôle dans l'équipe, date]

Si l'enseignant renvoie vers le détenteur des droits, reprendre le même message
en précisant les trois usages et le fichier exact (empreinte incluse), sans
élargir la portée demandée.

## Ce qui doit être archivé avant d'activer un garde-fou

- date et expéditeur de la réponse, avec son rôle / sa capacité à autoriser ;
- portée exacte : fichier visé (SHA-256), usage pédagogique, téléchargement
  automatisé, publication dérivée ;
- citation ou e-mail conservé avec son en-tête, ou lien vers un document signé ;
- mise à jour correspondante de `model/DATASET.md` et de la description de #18 ;
- décision explicite du propriétaire du dépôt pour `DATASET_USE_APPROVED` et
  `MODEL_ARTIFACT_PUBLISH_APPROVED`, et traitement séparé de la publication
  GHCR historique.

Tant que ces éléments ne sont pas réunis : ne pas activer les variables CI, ne
pas télécharger le classeur, ne pas publier l'artefact, ne pas déployer. Une
réponse orale, partielle ou un simple lien public ne suffisent pas.
