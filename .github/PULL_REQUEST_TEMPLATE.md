## Objet de cette Pull Request
Décrire brièvement les modifications et leur intérêt pour le pipeline DSCC.

**Issue liée :** Relates to #... *(ne remplacer par `Closes #N` que lorsque les critères d'acceptation de l'Issue N sont entièrement satisfaits)*

## Domaine / responsable
- [ ] R1 — Modèle ML & API
- [ ] R2 — Pipeline événementiel
- [ ] R3 — Infrastructure Azure & CI/CD
- [ ] R4 — Observabilité, dashboard & coûts
- [ ] Documentation / organisation

## Vérifications avant revue
- [ ] Contrat technique connu et vérifié ; signaler explicitement tout écart avec `docs/technical-contract.md` (notamment les 21 inputs du modèle, le batch versus unitaire pour `/predict`).
- [ ] Tests locaux exécutés et résultats indiqués.
- [ ] Capture ou preuve reproductible jointe lorsque nécessaire au rapport PDF.
- [ ] Aucun secret (token, clé Azure, connexion, `.env`, `local.settings.json`) commité.
- [ ] Coût ou impact Azure vérifié si la PR touche au Cloud.
- [ ] Branches ciblées et dépendances décrites.
- [ ] README / documentation mis à jour si nécessaire.

## Tests exécutés
Commande(s), environnement, résultat(s) :

```bash
# Préciser uniquement les commandes réellement exécutées
```

## Captures et preuves
Liens vers `docs/screenshots/`, journal ou captures (sans secrets) :

## Dépendances / risques / décisions à prendre
Indiquer toute Issue bloquante et les conséquences sur les autres lots.

## Revue
La branche `main` est protégée : **une approbation d'un autre membre est requise** avant la fusion. Les tests locaux déclarés ne remplacent pas une approbation GitHub ; ne pas clôturer une Issue qui dépend encore de tests d'intégration.
