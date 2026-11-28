# Plan de soutenance — 2 décembre 2026
**Langue : français.** 10 minutes + 5 minutes de questions. Répartition proposée, à valider collectivement.

| Temps | Intervenant | Sujet |
|---|---|---|
| 0:00–0:40 | Gémima | Problématique et objectifs |
| 0:40–1:40 | Gémima | Architecture événementielle |
| 1:40–3:10 | Elias | Modèle ONNX 1.1.0, 19 variables, métriques rapportées, API |
| 3:10–4:40 | Gémima | Pipeline, ETag, idempotence, reprises et rejet |
| 4:40–6:10 | Aminata | Infrastructure Azure, RBAC, OIDC et CI/CD |
| 6:10–7:40 | Omar | Dashboard, KQL, supervision et coûts |
| 7:40–9:15 | Équipe | Démonstration avec preuves |
| 9:15–10:00 | Gémima | Bilan, limites et nettoyage |

## Introduction proposée
Notre projet consiste à automatiser la prédiction du risque d'attrition des clients télécoms. Dès qu'un CSV est déposé, une architecture événementielle déclenche une chaîne d'inférence ONNX. Nous avons privilégié le découplage, la fiabilité des résultats, la maîtrise des coûts et la traçabilité.

## Démonstration
Suivre le [cahier de recette E01–E11](recette-azure.md) après les validations nécessaires. Préparer un CSV synthétique unique, relever UTC, vérifier /health et /version, observer sortie, métadonnées et dashboard. Montrer les preuves de rejet, poison, KQL, alerte, digest, coûts et scale-to-zero seulement si obtenues. En cas d'indisponibilité Azure, démontrer l'aperçu ONNX/Azurite et l'indiquer explicitement. Les captures mock ne constituent pas de preuve Azure.

## Preuves du 28 novembre
- 111 tests intégrés et 66/66 paires propres sur le snapshot #22 (46147650653, 46147650574), 2 ONNX + 3 Azurite (46147650662).
- #27 : 76 tests pipeline dans une exécution distincte (46141028861), également inclus dans les 111 du nouvel aperçu ; ne pas additionner.
- 4 tests ML CI hors dataset ; 8 tests locaux rapportés par Omar. Droits non réglés.
- OIDC lecture seule réussi (45966902708 tentative 2), quatre rôles humains attribués et relus ; what-if #29 corrigé : 20 Create, 1 Modify apparent, 2 NoChange. Pas de déploiement attesté.
- Coût estimé 2,42 USD ; budget RG 4 EUR/mois, consommation rapportée avant déploiement 0 EUR ; coût final non mesuré.

## Questions-réponses
- Pourquoi une file ? Découplage, absorption de charge et reprises.
- Exactly once ? Non : livraison au moins une fois ; persistance idempotente par blob+ETag.
- Pourquoi 19 variables ? Disponibilité temporelle des deux compteurs non prouvée.
- Pourquoi ONNX ? Portabilité et contrat versionné.
- Pourquoi OIDC ? Jetons temporaires sans secret Azure permanent.
- Comment contrôler les coûts ? Alertes, consommation, logs bornés, zéro réplica et nettoyage approuvé.
- Que reste-t-il à démontrer ? La recette réelle Azure, les droits et la release intégrée.

Répéter à quatre, chacun maîtrisant aussi un domaine voisin. Ajouter les preuves réelles et les temps de parole au Word collaboratif.

## Point de contrôle du 28 novembre — accès et intégration

La coordinatrice a exécuté dans Azure Cloud Shell les opérations suivantes : abonnement Azure for Students actif, groupe rg-projet-g2cc en francecentral, identification des trois comptes Entra, absence d'attribution individuelle retournée avant modification, création puis relecture de quatre attributions au périmètre du groupe : Aminata Contributor ; Elias Reader ; Omar Reader et Monitoring Contributor. Lien direct du groupe généré pour diffusion interne uniquement. Les captures 03–07 sont conservées pour le Word collaboratif ; aucune adresse électronique, identifiant d'abonnement ou lien contenant cet identifiant ne doit être publié. L'accès effectif de chacun reste à confirmer ; aucun provisionnement applicatif ni coût mesuré n'est attesté par cette opération. Voir [Issue #3, preuve RBAC](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/3#issuecomment-7240106239).

Le nouvel aperçu intégré #22 au SHA 5687bf4 inclut #18 fd1e6fe et #27 7c669a7 : **111 tests** (16 API, 76 pipeline, 2 ONNX, 17 Node), Ruff et gardes simulées réussis, [run 46147650653](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46147650653). [66/66 paires sans conflit](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46147650574) et [2 ONNX + 3 Azurite](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46147650662). Cette preuve remplace le précédent aperçu 107 tests pour le périmètre combiné, mais ne couvre pas la PR documentaire #28 ni les tests cloud. Elias a approuvé #19 ccb406c et #27 7c669a7 ; #19 a ensuite été fusionnée dans main. #18 conserve le blocage de droits, malgré le nouveau brouillon d'autorisation. Publication et déploiement restent désactivés.

## Mise à jour après fusion du dashboard — 28 novembre 2026

La PR #19, tête ccb406c, a été approuvée par Elias et par la coordinatrice sur autorisation explicite, puis fusionnée dans main au commit 9de9d5e. La branche feat/dashboard n'apparaît plus. La [CI de main 46169842338](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46169842338) confirme les jobs dashboard, API, pipeline, observabilité et lint réussis. Les deux échecs restants sont les gardes exigeant les fichiers training et tests d'intégration sur main (PR #18 et #22 ouvertes) ; publication ignorée. L'Issue #9 demeure ouverte pour la recette Azure réelle. Cinq PR restent ouvertes : #18, #22, #27, #28 et #29. L'aperçu 111 tests/66 paires est une preuve du snapshot #22 5687bf4, non une nouvelle CI de main. #27 approuvée indépendamment ; #29 attend sa revue ; déploiement non exécuté. Le rapport Word partagé demeure la référence.
