# Cahier de recette Azure — DSCC (Issue #11)

Version de préparation du 28 novembre 2026. **Aucun scénario cloud n'est encore validé.** Ce cahier en français reprend les identifiants E01–E11 du plan technique tests/e2e/README.md (PR #22). Il constitue une annexe du rapport Word collaboratif, non une autorisation de déploiement.

## Conditions d'entrée et ordre d'exécution

1. Faire relire et intégrer #29 ; confirmer le plan-base, le budget de 4 EUR/mois et la décision de provisionnement. Seule la propriétaire autorise apply-base. Vérifier immédiatement l'inventaire, la remise Cosmos réellement activée, le débit et les droits des identités ; arrêter en cas d'erreur, ne pas recréer ou basculer vers un service payant sans accord.
2. Confirmer les connexions des trois collaborateurs ; attribuer les droits de données strictement nécessaires (par exemple Blob Data Contributor au conteneur input pour un opérateur désigné). Les rôles de gestion Reader/Contributor ne garantissent pas les accès aux données.
3. Avant les applications : quotas Flex mémoire et Container Apps, intégration de #18/#19/#22/#27, droits dataset et artefact documentés, CI de main verte, digest approuvé, validation de l'exposition temporaire synthétique uniquement. Ne pas réutiliser l'image historique 1.0.0.
4. Déployer selon infra/DEPLOYMENT.md et les gardes du bootstrap, après autorisation séparée. Vérifier le dispatcher avant Event Grid. Ne pas lancer les tests de panne ni créer des alertes facturables sans accord.
5. Exécuter E07/E11, puis E01/E02/E06, E04/E05, E03, E08/E09 et E10 ; l'ordre est une proposition de recette, pas une preuve d'exécution. E10 commence avant tout trafic et se répète après la démonstration.

## Matrice de recette

| ID | Action / résultat attendu | Preuve à collecter | Responsable proposé | État |
|---|---|---|---|---|
| E01 | Déposer un CSV synthétique unique ; résultat versionné et métadonnée Cosmos en moins de 60 s | UTC dépôt, file, sortie, Cosmos, latence | Gémima + Aminata | Non exécuté |
| E02 | CSV invalide ; rejet JSON, aucune inférence ni valeur brute exposée | Rejet et logs expurgés | Gémima | Non exécuté |
| E03 | Injection isolée HTTP 503 autorisée ; cinq livraisons puis poison, aucune sortie de succès ; rétablir configuration | Dequeue count, poison queue, restauration | Aminata + Gémima | Non exécuté |
| E04 | Rejouer même événement/ETag, y compris concurrence ; une sortie canonique et une métadonnée, appels API multiples possibles | Compteurs Blob/Cosmos et logs | Gémima | Non exécuté |
| E05 | Remplacer le blob, puis rejouer ancien événement ; deux clés distinctes, ancien résultat préservé | ETags expurgés, résultats, statut superseded | Gémima + Aminata | Non exécuté |
| E06 | Nouveau lot valide ; dashboard actualisé après persistance dans l'intervalle de rafraîchissement, KPI corrects | API recent, capture datée | Omar | Non exécuté |
| E07 | Déploiement approuvé ; /health, /version correspondant au commit et Functions présentes | Run Actions, endpoints expurgés | Gémima + Aminata | Non exécuté |
| E08 | Observer après inactivité ; zéro réplica si configuration le permet | Graphique de réplicas, fenêtre UTC | Aminata | Non exécuté |
| E09 | Déclencher alerte avec trafic synthétique autorisé ; KQL, alerte et e-mail observés | Résultats KQL, historique alerte, notification expurgée | Omar | Non exécuté |
| E10 | Vérifier coûts au RG, RBAC et absence de secrets ; respecter enveloppe approuvée | Cost Analysis daté, droits, vérifications | Équipe | Précontrôles faits, recette non exécutée |
| E11 | Comparer digest GHCR approuvé, révision Container Apps et release ID /version | Digest, run, révision, JSON | Gémima + Elias | Non exécuté |

## Fiche de résultat à recopier dans le Word partagé

| Champ | Valeur à renseigner |
|---|---|
| Scénario / date UTC / opérateur | |
| SHA / version du modèle / environnement | |
| Identifiant du fichier synthétique | |
| Résultat attendu / résultat observé | |
| Durée / statut PASS, FAIL ou BLOQUÉ | |
| Capture ou lien de preuve interne | |
| Incident, correction, restauration éventuelle | |

Les preuves doivent être datées, sans données clients, jetons, secrets, adresses personnelles ni identifiants d'abonnement. Ne pas considérer les 111 tests hors cloud ou les 5 tests RBAC simulés comme une recette Azure. Les captures 03–21 documentent la préparation, non la création du socle. Le coût affiché au précontrôle est de 0 EUR pour le RG ; la facturation peut être différée. Après la soutenance, le nettoyage exige une autorisation séparée et une preuve d'absence des ressources.
