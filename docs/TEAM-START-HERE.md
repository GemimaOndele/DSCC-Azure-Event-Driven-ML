# DSCC — Fiche de démarrage de l'équipe

**Date de référence : 18 novembre 2026**  
**Soutenance : mercredi 2 décembre 2026**  
**Projet GitHub :** https://github.com/users/GemimaOndele/projects/5  
**Issues :** https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues

> Toutes les branches ci-dessous existent déjà sur GitHub. La création d'une branche ne signifie pas que le travail qui lui correspond est réalisé. Restez sur votre branche, n'écrivez pas directement dans `main`. La protection active exige une Pull Request et l'approbation d'un autre membre.

## 1. Qui commence quoi ?

| Membre | Travail immédiat | Branche existante | Issue | Livrable attendu |
|---|---|---|---|---|
| **Gémima** (@GemimaOndele) | Coordonner et faire valider le contrat CSV, API, queue, DB | `docs/technical-contract` | [#2](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/2) | Relecture et accord sur [PR #14](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/14), puis contrat versionné |
| **Aminata** (@yayeaminata12) | Relire/compléter la procédure d'accès partagé Azure, **sans encore créer de ressource** | `docs/azure-sharing` | [#3](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/3) | [PR #15](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/15) validée, guide clair, décisions et captures |
| **Elias** (@eliascre) | Préparer le jeu de données Telecom Churn, script de nettoyage et entraînement local | `feat/ml-training` | [#4](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/4) | `model/`, mesures (F1 et ROC-AUC + baseline), modèle versionné |
| **Omar** (@omk181920) | Termine d'abord son TP ; au retour, contribuer au dashboard / KQL | `feat/dashboard`, puis `feat/observability` | [#9](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/9), [#10](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/10) | Dashboard et requêtes KQL une fois les données disponibles |

**Relais d'Omar :** Gémima peut préparer un tableau de bord minimal, et Aminata/Gémima peuvent commencer la supervision nécessaire aux tests ; le pipeline ne doit **pas** dépendre du retour d'Omar.

## 2. Branches pour la suite

| Branche | Domaine | Quand commencer ? |
|---|---|---|
| `feat/ml-api` | Elias — FastAPI, Docker, pytest, GHCR | Dès que le modèle / format `POST /predict` est convenu (#5) |
| `feat/event-pipeline` | Aminata + Gémima — dispatcher, worker, recent, Azurite | Après validation des formats de #2, en local (#6) |
| `infra/azure-core` | Aminata (R3) + Gémima — RG, régions, quotas, scripts Azure | Après choix de l'abonnement et décision de budget (#7) ; **aucun provisionnement sans accord** |
| `feat/dashboard` | Gémima en relais, Omar à son retour | Maquette avec données simulées après contrat (#9) |
| `feat/observability` | Gémima en relais, Omar à son retour | Préparer le plan de mesure sans Azure, déployer plus tard (#10) |
| `chore/issue-pr-templates` | Gémima, relecture Elias | [PR #16](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/16) à approuver |
| `docs/project-management` | Historique de préparation du planning | Le document de planification a déjà été fusionné dans `main` (PR #13) |

**Note de coordination :** les branches `feat/event-pipeline` et `infra/azure-core` sont partagées par le binôme. Avant de pousser, prévenir l'autre membre et faire `git pull --ff-only` pour limiter les conflits. Pour des changements simultanés importants, créer une branche temporaire distincte et ouvrir une PR vers la branche fonctionnelle.

## 3. Démarrer localement : commandes pour chacun

### Premier clonage

```bash
git clone https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML.git
cd DSCC-Azure-Event-Driven-ML
git fetch origin
git branch -a
```

### Se placer sur **sa branche existante**

Exemple Elias :

```bash
git switch --track origin/feat/ml-training
```

Exemple Aminata :

```bash
git switch --track origin/docs/azure-sharing
```

Exemple Gémima :

```bash
git switch --track origin/docs/technical-contract
```

Exemple Omar :

```bash
git switch --track origin/feat/dashboard
```

Si la branche existe **déjà localement**, utiliser `git switch <nom-de-branche>` au lieu de `git switch --track ...`. Ne pas utiliser `git checkout -b` pour recréer une branche déjà suivie.

### Faire une petite contribution

```bash
git status
git add <fichiers-vérifiés>
git commit -m "feat: description courte"
git push -u origin <nom-de-votre-branche>
```

Ouvrir ensuite une Pull Request vers `main` depuis GitHub et référencer l'Issue (ex. `Closes #4` après réalisation complète ; sinon `Relates to #4`).

## 4. Dépendances qui comptent

- Contrat technique **#2** à valider avant de figer les schémas de la **#5** API, de la **#6** Functions et de la **#9** persistance/dashboard.
- Elias peut **commencer #4** en local avant la validation finale du contrat, mais doit s'accorder sur la liste de features et le format de prédiction.
- Aminata peut **terminer la documentation #3** sans ressource Azure ni accès partagé déjà configuré.
- `infra/azure-core` et le déploiement #7 attendent le choix de l'abonnement entre Gémima et Aminata, la région/quota autorisés et le budget.
- CI locale #8 peut commencer dès que les premiers tests existent ; déploiement CD/OIDC après l'infrastructure.
- Omar est **non bloquant** : l'équipe active réalise la version minimale nécessaire à la note s'il est encore indisponible.

## 5. Règles GitHub et statut réel

- **`main` protégée et active :** PR obligatoire, une approbation, suppression et force push interdits.
- [PR #14](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/14) : contrat + README + CONTRIBUTING + .gitignore, ouverte, revue d'Aminata et d'Elias demandée.
- [PR #15](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/15) : guide Azure, ouverte, revue d'Aminata demandée.
- [PR #16](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/pull/16) : modèles d'Issues et de PR, ouverte, revue d'Elias demandée.
- **GitHub Projects :** Kanban et Roadmap créés ; **restent à vérifier/remplir** les dates cibles, Priority, Workstream, dépendances natives et accès de tous les membres au tableau privé. Les fiches Issues décrivent déjà les échéances et les dépendances en texte.
- **Vidéo : facultative**, selon l'annonce orale de l'enseignante ; rapport PDF avec captures d'étapes obligatoire.
- **Azure :** une seule souscription d'intégration, plafond total 25 USD, pas de VM/GPU/AKS, pas de secrets dans le dépôt.

## 6. Règle quotidienne de suivi

Après chaque séance, chaque membre ajoute à son Issue un bref commentaire : **ce qui est fait, lien vers la branche/PR, tests/captures réalisés, obstacle éventuel, prochaine action**. Les heures réelles, les décisions, les restrictions Azure et les preuves du rapport sont consignées aussi dans le Word collaboratif.

**Ne pas mettre « Terminé » avant une preuve ou une validation concrète.** Les dates sont des objectifs internes à confirmer avec l'équipe ; soutenance le 2 décembre 2026.
