# 19 vs 21 features — décision et ablation reproductible (PR #18)

**Décision actée le 27/11/2026 (Elias, lot R1/R4) : 19 features.** Les colonnes
`numAdminTickets` et `numTechTickets` sont retirées du modèle livré `1.1.0` :
leur disponibilité avant `Churn` n'est pas documentée dans le classeur du cas.
Le modèle `1.0.0` à 21 features est conservé uniquement comme preuve
historique/ablation ; il n'est plus l'artefact partagé entre #17 et #18.

## Pourquoi cette mesure

`model/DATASET.md` §3 documente que les deux compteurs proviennent du classeur
du cas DSCC sans horodatage publié : leur antériorité par rapport à la
résiliation **ne peut pas être certifiée**. `model/ablation_19.py` réentraîne
exactement le même pipeline (graine 42, split stratifié 80/20, imputation
médiane, standardisation, one-hot, régression logistique équilibrée) dans les
deux configurations. Le script est **en lecture seule** : il n'écrit ni modèle,
ni métriques, ni split.

```bash
py -3.12 model/ablation_19.py
```

## Résultats (1 409 lignes de test, graine 42)

| Jeu de features | AUC | F1 | Accuracy | Matrice de confusion | Accuracy baseline |
|---|---:|---:|---:|---|---:|
| **19 — modèle `1.1.0` livré** | **0,8413** | **0,6136** | **0,7381** | `[[747, 288], [81, 293]]` | 0,7346 |
| 21 — ancien modèle `1.0.0` | 0,9273 | 0,7328 | 0,8318 | `[[847, 188], [49, 325]]` | 0,7346 |

Écart attribuable aux deux compteurs : **+0,0860 AUC**, **+0,1192 F1**,
**+0,0937 accuracy** lorsqu'ils sont ajoutés. Le modèle à 19 features conserve
un vrai signal (AUC 0,84, F1 0,61) mais son accuracy est proche de la baseline
`most_frequent` (0,7346) : le rapport doit le dire explicitement.

## Conséquences de la décision

- Les compteurs restent présents dans le classeur source épinglé, mais
  `model/train.py` les exclut explicitement ; `model/features.json` ne les
  expose plus à l'API.
- L'artefact ONNX `1.1.0` remplace `1.0.0` dans #17 et #18 (blob Git partagé
  `09ee933f16731e7218189d19d7c3ab98162de34e`). Les anciens binaires sont
  retirés de l'arbre courant pour éviter deux modèles concurrents.
- Le contrat #14, le worker #21, la CI #23 et le tableau de bord #19 doivent
  être alignés sur 19 entrées et la version `1.1.0` avant intégration.
- L'autorisation du classeur DSCC et la diffusion de l'artefact dérivé restent
  des décisions distinctes, non tranchées ici (`model/DATASET.md` §4).
