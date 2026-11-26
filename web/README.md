# Tableau de bord statique — Issue #9 (`feat/dashboard`)

Page HTML/JS (Chart.js) hébergée dans le conteneur `$web` du compte de stockage
(§4.4 du sujet). Elle lit `GET /api/recent` (fonction `recent` de #6) et s'actualise
**toutes les 30 s**, sans aucune action manuelle.

| Fichier | Rôle |
|---|---|
| `index.html` | Structure : KPI, graphique, tableau des 20 dernières inférences |
| `data.js` | Validation complète du contrat, agrégats et génération simulée bornée |
| `app.js` | Appel `/api/recent`, délai d'expiration de 10 s, rendu, boucle de 30 s |
| `config.js` | URL publique de la Function App (**aucun secret**) |
| `style.css` | Thème clair/sombre, mise en page responsive |
| `sample-recent.json` | Données **fictives** pour le mode simulé (même schéma que `/api/recent`) |

## Contrat consommé

Schéma produit par `functions/src/service.py` (`recent`) :

```json
{ "count": 8, "limit": 20, "results": [
  { "id": "...", "fileName": "batch_01.csv", "timestamp": "2026-11-24T09:00:00Z",
    "rows": 50, "atRisk": 13, "avgChurnProbability": 0.31,
    "modelVersion": "1.0.0", "durationMs": 1840, "status": "ok" } ] }
```

Affichage :

- **KPI** : nombre de fichiers, clients scorés, clients à risque (et leur part),
  probabilité moyenne **pondérée par le nombre de clients**, durée moyenne par fichier,
  version(s) du modèle ;
- **graphique** : barres empilées « à risque / non à risque » par fichier, avec la
  probabilité moyenne sur un second axe ;
- **tableau** : les 20 dernières inférences, triées de la plus récente à la plus ancienne.
  Une ligne passe en orange quand au moins 30 % des clients du fichier sont à risque.

Robustesse : tout le texte venant de l'API est inséré via `textContent` (aucune
injection HTML). En cas d'erreur réseau ou de délai dépassé, un bandeau s'affiche, les
dernières données restent visibles et un nouvel essai a lieu au cycle suivant. La réponse entière est validée avant rendu ; les probabilités absentes sont exclues de la moyenne pondérée, pas transformées en zéro. Le mode simulé reste limité à 20 résultats.  Si
aucune inférence n'existe, un état vide s'affiche. L'actualisation est suspendue quand
l'onglet est masqué, puis reprend dès qu'il redevient visible. Chart.js est épinglé
(4.4.1) avec une empreinte SRI.

## Exécution locale (sans Azure)

```bash
py -3.12 -m http.server 8090 --bind 127.0.0.1 --directory web
# http://127.0.0.1:8090/           → mode simulé (apiBaseUrl vide)
# http://127.0.0.1:8090/?mock=1    → mode simulé forcé
```

En mode simulé, chaque actualisation ajoute un fichier fictif (`simulated_batch_NNN.csv`)
pour montrer le rafraîchissement automatique. Le badge « Données simulées » l'indique
clairement : ces captures ne doivent **pas** servir de preuve Azure dans le rapport.

Avec la Function App locale (`func start --script-root functions --port 7071`), mettre
`apiBaseUrl: "http://localhost:7071"` dans `config.js` et
`DASHBOARD_ORIGIN=http://127.0.0.1:8090` dans `local.settings.json`.

## Déploiement sur `$web` (après #7)

```bash
# Variables de l'abonnement d'intégration (voir commandes de référence §6 du sujet)
RG=rg-projet-<equipe>; ST=st<equipe>pipe; FUNC=func-<equipe>

# 1. URL publique du site statique (origine à autoriser)
WEB_ORIGIN=$(az storage account show -n $ST -g $RG \
  --query "primaryEndpoints.web" -o tsv | sed 's:/*$::')

# 2. La fonction recent n'expose l'en-tête CORS que pour cette origine exacte
az functionapp config appsettings set -n $FUNC -g $RG \
  --settings DASHBOARD_ORIGIN=$WEB_ORIGIN

# 3. Renseigner l'URL de la Function App dans web/config.js
#    apiBaseUrl: "https://$(az functionapp show -n $FUNC -g $RG --query defaultHostName -o tsv)"

# 4. Publier la page (identité Azure AD, pas de clé de compte)
az storage blob upload-batch --account-name $ST --auth-mode login \
  --destination '$web' --source web --overwrite
```

Ne pas activer **en plus** le CORS de la plateforme Function App pour la même origine :
l'en-tête est déjà posé par le code de `recent`, et un doublon ferait échouer la
requête dans le navigateur.

## Preuves à capturer (rapport / issue #9)

1. Tableau de bord en mode **Azure** (badge « Données Azure ») avec l'URL `$web` visible.
2. Dépôt d'un nouveau CSV dans `input/` puis, **sans recharger la page**, apparition de la
   ligne dans les 30 s suivantes (capture avant/après avec les horodatages).
3. Onglet Réseau du navigateur montrant `GET /api/recent` → 200 avec
   `Access-Control-Allow-Origin` égal à l'origine `$web`.

## Tests automatisés

`node --test tests/dashboard/test_data.cjs` : validation, dates, types, bornes, doublons, agrégats, taille du mode simulé. Le run 45884040393 a confirmé 16 tests réussis. Une recette navigateur et Azure reste nécessaire.
