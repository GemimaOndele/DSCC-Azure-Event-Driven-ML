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
Préparer un CSV synthétique unique, relever UTC, vérifier /health et /version, observer sortie, métadonnées et dashboard. Montrer les preuves de rejet, poison, KQL, alerte, digest, coûts et scale-to-zero seulement si obtenues. En cas d'indisponibilité Azure, démontrer l'aperçu ONNX/Azurite et l'indiquer explicitement. Les captures mock ne constituent pas de preuve Azure.

## Preuves du 28 novembre
- 107 tests intégrés et 55/55 paires propres sur le snapshot #22 (46140778592, 46140778562), 2 ONNX + 3 Azurite (46140778585).
- #27 : 76 tests pipeline dans une exécution distincte (46141028861), non incluse dans les 107.
- 4 tests ML CI hors dataset ; 8 tests locaux rapportés par Omar. Droits non réglés.
- OIDC lecture seule réussi (45966902708 tentative 2), pas de déploiement attesté.
- Coût estimé 2,42 USD ; coût réel non mesuré.

## Questions-réponses
- Pourquoi une file ? Découplage, absorption de charge et reprises.
- Exactly once ? Non : livraison au moins une fois ; persistance idempotente par blob+ETag.
- Pourquoi 19 variables ? Disponibilité temporelle des deux compteurs non prouvée.
- Pourquoi ONNX ? Portabilité et contrat versionné.
- Pourquoi OIDC ? Jetons temporaires sans secret Azure permanent.
- Comment contrôler les coûts ? Alertes, consommation, logs bornés, zéro réplica et nettoyage approuvé.
- Que reste-t-il à démontrer ? La recette réelle Azure, les droits et la release intégrée.

Répéter à quatre, chacun maîtrisant aussi un domaine voisin. Ajouter les preuves réelles et les temps de parole au Word collaboratif.
