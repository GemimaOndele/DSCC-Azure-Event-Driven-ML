# Organisation du projet — GitHub Projects

**Projet :** DSCC — Projet Azure ML | Conseil d'équipe  
**GitHub Project :** https://github.com/users/GemimaOndele/projects/5  
**Dépôt :** https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML  
**Date de cadrage :** 18 novembre 2026  
**Soutenance :** 2 décembre 2026  
**Sujet validé par les quatre membres :** Telecom Customer Churn — pipeline de ML événementiel sur Azure.

> Ce document prépare la configuration opérationnelle de GitHub Projects. Les dates et responsables ci-dessous sont **proposés** : les champs du tableau Projects ne sont pas modifiés automatiquement par ce fichier. Ne pas confondre une tâche documentée avec une tâche effectuée.

## 1. Membres, disponibilité et domaines

| Membre | Responsabilité actuelle | Domaines | Disponibilité |
| --- | --- | --- | --- |
| Gémima ONDELE POUROU | Coordination, GitHub, contrat commun, CI/CD, binôme Azure, rapport | Pilotage, R2/R3/R4 | Active |
| Yaye Aminata DIAGNE | Documentation d'accès partagé Azure d'abord, puis infrastructure et pipeline avec Gémima | R2/R3 | Active ; ne provisionne pas de ressources Azure pour l'instant |
| Elias CREMNITER | Données, entraînement, métriques, FastAPI, Docker et tests | R1 | Active |
| Omar KRARTI | Dashboard, requêtes KQL, vérification des preuves et documentation à son retour | R4 | Temporairement indisponible (termine un TP) |

## 1.1 Comptes GitHub et assignations vérifiées (18 novembre 2026)

| Membre | GitHub | Autorisation constatée | Action |
| --- | --- | --- | --- |
| Gémima | [@GemimaOndele](https://github.com/GemimaOndele) | Administration | Coordination du dépôt et du tableau |
| Aminata | [@yayeaminata12](https://github.com/yayeaminata12) | Écriture | Assignée à #2, #3, #6, #7, #8, #11 et #12 |
| Elias | [@eliascre](https://github.com/eliascre) | Écriture | Assignations GitHub confirmées sur #2, #4, #5 et #11 |
| Omar | [@omk181920](https://github.com/omk181920) | Écriture | Assigné à #9, #10 et #12 ; reste temporairement indisponible, sans blocage du chemin critique |

Les Issues #6 et #7 sont attribuées à Aminata et Gémima en binôme. Les Issues #9 et #10 sont attribuées à Omar et Gémima, avec Gémima en relais le temps qu'Omar termine son TP. Les Issues #2 et #11 sont attribuées aux trois membres actifs ; #12 est attribuée aux quatre membres. Les droits du dépôt et ceux du **GitHub Project privé** sont distincts : vérifier l'accès de chacun au tableau pour qu'il puisse le modifier.

**Règle :** aucune tâche essentielle au démarrage, à l'intégration ou à la soutenance ne doit dépendre exclusivement d'Omar. Gémima et Aminata assurent un relais minimal sur le dashboard et l'observabilité si nécessaire.

**Azure :** Gémima et Aminata disposent des crédits les plus élevés. Choisir **un seul abonnement d'intégration** après vérification des crédits, restrictions régionales et quotas. Le propriétaire crée les rôles et ressources ; les autres peuvent collaborer par accès RBAC si autorisé ou en développant localement et en déployant via GitHub Actions/OIDC.

## 2. Définition des statuts GitHub Projects

- **À faire** : tâche identifiée, pas encore commencée.
- **En cours** : un membre a réellement commencé et maintient la carte à jour.
- **En revue** : travail soumis à validation, tests ou Pull Request.
- **Terminé** : critères de validation remplis, captures/preuves enregistrées.
- **Bloqué** : impossibilité avérée d'avancer (dépendance technique, accès, quota, décision) ; expliquer le blocage dans l'Issue, le responsable de la résolution et sa prochaine action.

Ne pas placer automatiquement les tâches d'Omar dans « Bloqué » : elles sont **À faire**, avec une solution de relais et un démarrage différé. Un statut facultatif **Prêt à démarrer** peut être ajouté plus tard si le volume de tâches le justifie.

## 3. Champs Projects à créer

| Champ | Type recommandé | Valeurs / utilisation |
| --- | --- | --- |
| Priority | Sélection unique | P0 (bloquant / échéance rapprochée), P1 (important), P2 (amélioration) |
| Target date | Date | Date limite interne, non date imposée par l'enseignante |
| Workstream | Sélection unique | Pilotage, R1 ML/API, R2 Pipeline, R3 Azure/CI-CD, R4 Observabilité & Dashboard, Livraison |
| Responsable | Champ natif Assignees | Assigner seulement après invitation des comptes GitHub |
| Evidence | Texte court (facultatif) | Chemin de capture, lien vers preuve ou commentaire d'Issue |
| Source Excel | Texte court (facultatif) | Numéro d'étape dans les 52 étapes d'Aminata |

Les dépendances natives **Blocked by / Blocking** peuvent relier les Issues. Les références `#N` ci-dessous donnent la structure de départ.

## 4. Backlog priorisé et planifié

| Issue | Lot | Pilote fonctionnel | Priority | Date cible | Dépendances / conditions |
| --- | --- | --- | --- | --- | --- |
| [#1](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/1) | GitHub Projects, accès, règles | Gémima | P0 | 19 nov. | Aucune |
| [#2](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/2) | Contrat CSV, Queue, /predict, Cosmos | Gémima + validation Aminata et Elias | P0 | 19 nov. | Aucune |
| [#3](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/3) | Guide de partage Azure RBAC/OIDC | Aminata (+ Gémima) | P0 | 20 nov. | Aucune ; documentation d'abord |
| [#4](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/4) | Modèle Telecom Churn | Elias | P0 | 22 nov. | Validation de #2 pour le format d'inférence |
| [#5](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/5) | API, tests, Docker, GHCR | Elias | P0 | 24 nov. | #4 pour l'API finale ; squelette possible avant |
| [#6](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/6) | Functions dispatcher/worker/recent en local | Aminata + Gémima | P0 | 26 nov. | #2 ; pas d'Azure nécessaire pour les tests locaux |
| [#7](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/7) | Budget, régions, infra Azure | Aminata + Gémima | P0 | 26 nov. | #3, choix du compte, restrictions/quotas validés |
| [#8](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/8) | CI/CD & OIDC | Gémima (+ Aminata) | P0 | 28 nov. | Tests de #5 pour CI ; #7 pour déploiement CD |
| [#9](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/9) | Dashboard / persistance | Gémima au départ, Omar ensuite si disponible | P1 | 29 nov. | #2 pour maquette ; #6 et #7 pour données réelles |
| [#10](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/10) | Observabilité, KQL, alertes | Gémima/Aminata, puis Omar si disponible | P0 | 29 nov. | #7 et premières traces de #5/#6 |
| [#11](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/11) | Tests E2E et captures | Équipe active | P0 | 30 nov. | #5–#10 selon scénario ; tester tôt par morceau |
| [#12](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/12) | Rapport, coûts, soutenance, nettoyage | Toute l'équipe, Gémima coordonne | P0 | 1er déc. rapport ; 2 déc. soutenance ; nettoyage ensuite | Documentation tout au long du développement |

Les dates correspondent à une **planification interne proposée**. Le QCM du 24 novembre doit être pris en compte dans la charge de travail. Le rendu est un rapport PDF avec captures et documentation ; la **vidéo est optionnelle** selon l'enseignante.

## 5. Dépendances et parallélisation

1. Le contrat **#2** débloque les interfaces entre l'API (#5), le pipeline (#6) et le dashboard (#9).
2. Elias commence la préparation et l'entraînement **#4** en local, sans attendre l'abonnement Azure.
3. Aminata réalise la documentation d'accès **#3** en parallèle ; Gémima pilote **#1** et **#2**.
4. Après le contrat, le pipeline **#6** est développé avec Azurite et des réponses d'API simulées ; il peut donc progresser en parallèle de **#4/#5**.
5. L'infrastructure **#7** dépend de la validation du compte et de la région, mais pas du modèle terminé.
6. **#8** commence par la CI (sans Azure) ; le CD nécessite l'identité OIDC et la plateforme (#7).
7. **#9** peut démarrer avec des jeux de résultats fictifs. **#10** peut préparer les requêtes KQL avant les premières traces.
8. **#11** vérifie le bout-en-bout, les rejets, les reprises, la file poison, l'idempotence, le dashboard et les preuves.
9. **#12** commence immédiatement (journal, décisions, captures) et se termine après la soutenance par le nettoyage Azure.

## 6. Vues à configurer dans Projects

- **Vue 1 / Table** : toutes les Issues, `Assignees`, `Status`, `Priority`, `Target date`, `Workstream` ; trier par échéance puis priorité.
- **Kanban — Suivi des tâches** : disposition Board, champ de colonnes `Status`, cinq statuts ci-dessus ; glisser-déposer une carte uniquement lorsque son état change réellement.
- **Roadmap — Échéances** : nouvelle vue Roadmap, champ de date `Target date`, bornes novembre–décembre 2026.
- **Par membre (facultatif)** : vue Table, groupée par `Assignees`.

Le projet est **privé** sur la capture d'écran : inviter les autres membres dans les paramètres d'accès Projects ; inviter séparément les collaborateurs au dépôt si nécessaire. Ces deux accès ne sont pas forcément équivalents.

## 7. Conventions Git et qualité

- `main` : branche stable ; éviter tout commit direct de fonctionnalité.
- Branches courtes liées aux Issues : `docs/project-management`, `docs/azure-sharing`, `feat/ml-training`, `feat/ml-api`, `feat/event-pipeline`, `infra/azure-core`, `feat/dashboard`, `feat/observability`.
- Une PR avec description, Issue associée, tests/captures si pertinents, et relecture avant fusion.
- Ne jamais ajouter mot de passe, jeton, secret Azure, clé de stockage ou fichier de connexion sensible dans GitHub.
- Utiliser les commentaires de l'Issue pour documenter un blocage ; tenir à jour le Word partagé pour le journal de temps et le rapport.

## 8. Checklist de configuration

- [x] Dépôt créé, `main` disponible et 12 Issues importées dans GitHub Projects (confirmé par capture).
- [x] Vue Kanban et statuts `À faire`, `En cours`, `En revue`, `Terminé`, `Bloqué` (confirmés par capture).
- [x] Issue #1 déplacée en `En cours` (confirmée par capture).
- [ ] Ajouter les champs `Priority`, `Target date`, `Workstream`.
- [ ] Créer et régler la vue `Roadmap`.
- [ ] Renseigner les priorités et échéances dans les **champs natifs** de Projects (table de la section 4).
- [ ] Relier les dépendances natives entre les Issues pertinentes.
- [x] Membres invités au dépôt et assignations GitHub effectuées sur les 12 Issues avec les usernames vérifiés.
- [ ] Vérifier le partage du tableau Projects privé et du dépôt public.
- [ ] Réviser le plan et commencer les tâches en parallèle.
