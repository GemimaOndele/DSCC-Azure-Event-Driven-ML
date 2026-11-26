# 19 vs 21 features — quantified ablation (decision aid, PR #18)

**Statut :** preuve complémentaire pour la décision ouverte dans l'issue #2 / #4,
**pas un changement de contrat**. L'artefact ONNX `1.0.0` partagé avec la PR #17
reste inchangé ; `model/features.json` conserve ses 21 entrées.

## Pourquoi cette mesure

`model/DATASET.md` §3 documente que `numAdminTickets` et `numTechTickets`
proviennent du classeur du cas DSCC sans horodatage publié : leur disponibilité
avant la résiliation (`Churn`) **ne peut pas être certifiée**. La question
« 19 ou 21 features ? » reste donc ouverte. Afin de rendre l'arbitrage chiffré,
`model/ablation_19.py` réentraîne exactement le même pipeline (graine 42, split
stratifié 80/20, imputation médiane, standardisation, one-hot, régression
logistique équilibrée) avec et sans ces deux colonnes. Le script est **en lecture
seule** : il n'écrit ni modèle, ni métriques, ni split.

```bash
py -3.12 model/ablation_19.py
```

## Résultats (1 409 lignes de test, graine 42)

| Jeu de features | AUC | F1 | Accuracy | Matrice de confusion | Accuracy baseline |
|---|---:|---:|---:|---|---:|
| **21** (artefact commité) | **0,9273** | **0,7328** | **0,8318** | `[[847, 188], [49, 325]]` | 0,7346 |
| **19** (sans tickets) | 0,8413 | 0,6136 | 0,7381 | `[[747, 288], [81, 293]]` | 0,7346 |

Écart attribuable aux deux compteurs : **−0,0860 AUC**, **−0,1192 F1**,
**−0,0937 accuracy** lorsqu'ils sont retirés. Le modèle à 19 features conserve
un vrai signal (AUC 0,84 et F1 0,61 nets au-dessus de la baseline `most_frequent`,
dont le F1 est nul), mais l'accuracy revient au niveau de cette baseline.

## Interprétation et recommandation

- Ces chiffres ne prouvent **pas** une fuite temporelle : ils mesurent seulement
  la dépendance des métriques annoncées envers deux colonnes dont l'antériorité
  n'est pas documentée. Si elles ont été agrégées après la résiliation, les
  métriques `0,9273 / 0,7328` sont optimistes.
- Pour la démonstration pédagogique DSCC, conserver les 21 features est
  défendable **à condition** de toujours présenter la réserve de `DATASET.md` §3
  et cette ablation dans le rapport. C'est l'état actuel du dépôt.
- Pour toute affirmation « production-ready », il faut retirer les compteurs,
  réentraîner, republier `model/features.json` (19 features), remplacer l'ONNX
  partagé par #17, mettre à jour le contrat du worker (#21), les métriques et les
  preuves. Ce changement de contrat doit être décidé par l'équipe et appliqué via
  PR : il ne peut pas être fait silencieusement dans une branche.

Aucune de ces options n'est tranchée ici ; cette note fournit les éléments de
décision demandés aux relecteurs de la PR #18 et à l'issue #2.
