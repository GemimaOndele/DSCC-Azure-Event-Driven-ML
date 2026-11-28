# Registre des preuves et journal d'équipe — Issue #12
**Point de contrôle : 28 novembre 2026.** Les durées individuelles doivent être renseignées par les membres eux-mêmes (cible pédagogique : 12 h/personne). Le Word OneDrive partagé est le rapport de référence. Aucun temps déduit des durées CI.

## Historique vérifiable
Le registre antérieur complet reste accessible dans [le snapshot main fce70111](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/blob/fce70111aef1bc62a024c7a20d9913891f5727ef/docs/evidence-register.md), y compris les essais historiques à 21 variables et les incidents de répétition des fusions. Ces résultats ne sont pas les preuves du modèle 1.1.0.

| Date | Périmètre | Preuve / résultat |
|---|---|---|
| 24/11 | #15 guide Azure d'Aminata | Fusion fae1d19 |
| 27/11 | #24 infrastructure | Fusion e56f77c, compilation et gardes, sans déploiement |
| 27/11 | OIDC | Premier essai AADSTS700213 ; [tentative 2 réussie](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45966902708/attempts/2) en lecture seule |
| 27/11 | #26 | Correctif sujet OIDC a3f5b233, CI 45970191053, fusion c67bafc |
| 27/11 | #14 contrat 19 variables | Fusion 3e298c1 |
| 27/11 | #17 API | Fusion 1357387 ; 16 tests, Ruff et Docker [45961769605](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45961769605) |
| 27/11 | #18 modèle | e7d8272, 4 tests hors dataset, 4 désélectionnés [45961524670](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45961524670), droits non établis |
| 27/11 | #21 pipeline | Fusion 0f2d4f2 ; 72 tests [45962557654](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45962557654) |
| 27/11 | #23 CI/CD | Fusion b519575 ; gate dynamique historique 107 tests, image 100599122 octets [45964640260](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45964640260) |
| 27/11 | #20 supervision | Fusion b437f62 ; gardes simulées, alertes Azure non prouvées |
| 27/11 | #25 rapport initial | Fusion fce70111 |
| 27/11 | CI main fce70111 | [45990705903](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/45990705903) : échec des gates de présence des composants ML/dashboard/E2E ; preuve historique de ce SHA, pas de nouveau run main vérifié |

## Contrôles du 28 novembre
| Périmètre | SHA et résultats vérifiés |
|---|---|
| #19 dashboard | ccb406c ; 17 tests Node dans l'aperçu intégré |
| #22 intégration séquentielle | 13f1b75 ; 107 tests (16 API, 72 pipeline, 2 ONNX, 17 Node), Ruff et gardes simulées [46140778592](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46140778592) |
| #22 fusions | 55/55 paires propres [46140778562](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46140778562) |
| #22 ONNX/Azurite | 2 + 3 tests [46140778585](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46140778585) |
| #27 plafonnement RECENT_LIMIT | 7c669a7 ; 76 tests, dont 4 supplémentaires, Ruff [46141028861](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46141028861) |
| #27 CI intégrée | Succès sur branche avec étapes conditionnelles potentiellement ignorées [46141028906](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/actions/runs/46141028906) |

#27 est hors du snapshot des 107 tests ; une nouvelle preuve combinée est nécessaire. Le 28/11, Elias a commenté #18, #19, #22, #27 et #28 sans approbation formelle. L'approbation d'Omar sur #18 e7d8272 ne lève pas les réserves de droits ni la demande de modifications antérieure. Ne pas extrapoler une validation d'un SHA à un autre.

## Journal et recette
Pour chaque séance : date UTC, membre, durée réelle, issue/PR, SHA, environnement, test, attendu/observé, preuve, incident et correction. Pour Azure : IAM, quotas, Free Tier, what-if, déploiement/version, E01–E11, KQL/alerte, coût réel et nettoyage. Ne pas publier de secrets, données brutes ou identifiants sensibles. Aucune recette cloud complète ni coût mesuré attestés. Les champs natifs de GitHub Projects restent non vérifiés.
