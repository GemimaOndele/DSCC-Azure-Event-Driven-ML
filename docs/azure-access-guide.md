# Guide de collaboration Azure — DSCC Telecom Churn

**Statut : Brouillon de procédure, à relire et valider par Aminata (R3) et Gémima (coordination / accès Azure). Mise à jour des responsabilités R4 : 24/11/2026.**  
**Source principale :** message d'Aminata « Comment partager la partie Azure », reçu le 18/11/2026.  
**Référence de gestion :** [Issue #3](https://github.com/GemimaOndele/DSCC-Azure-Event-Driven-ML/issues/3).

## 1. Principe et responsables

- **Un seul abonnement Azure for Students** retenu après comparaison des crédits de Gémima et d'Aminata, des régions et des quotas.
- **Un groupe de ressources** proposé : `rg-projet-g2cc` (à valider avant création).
- **R3 = Aminata** : pilotage de l'infrastructure et du déploiement ; documentation initiale avant tout provisionnement.
- **R4 = Omar** : disponible depuis le 24/11/2026 et désormais pilote du dashboard, de la supervision, des métriques et des alertes ; **Gémima** assure la coordination générale et l'appui à l'intégration R4/R3 avec Aminata.
- **R1 = Elias**, ML/API local ; **R2 = Gémima + Aminata**, pipeline local.
- **Propriétaire Azure** : celui ou celle dont l'abonnement est retenu ; il s'agit de Gémima ou d'Aminata, **indépendamment du numéro de lot R3/R4**. Le membre de binôme non propriétaire peut recevoir le rôle Contributor sur le groupe, si son identité est disponible dans le même tenant (ou via un invité Entra B2B).
- Ne JAMAIS partager une session Microsoft, un mot de passe, un token ou une clé.

## 2. Accès RBAC ciblé au groupe

**Préconditions :** `rg-projet-g2cc` créé sur l'abonnement retenu et droit du propriétaire de gérer les attributions de rôles. Vérifier d'abord le tenant Microsoft Entra de chacun.

Dans le **bon tenant**, la personne à inviter ouvre **son propre** Cloud Shell :

```bash
az ad signed-in-user show --query id -o tsv
```

Cette commande rend l'ID objet de l'utilisateur connecté dans son **tenant courant**. Si la personne à inviter est dans un autre tenant, il faut d'abord l'inviter comme utilisateur **B2B guest** et utiliser l'ID objet de ce compte **invité dans le tenant propriétaire** (l'ID d'origine n'est pas interchangeable).

Sur Cloud Shell du propriétaire, après avoir défini le bon abonnement et la variable `RG` :

```bash
source ~/projet.env
az role assignment create --role Contributor \
  --assignee-object-id <ID-OBJET-DANS-LE-TENANT-PROPRIETAIRE> \
  --assignee-principal-type User \
  --scope "$(az group show -n "$RG" --query id -o tsv)"
```

**Important :** `~/projet.env` reste local et ne doit **jamais** être commité s'il contient des données sensibles. L'accès du membre invité est limité au RG ciblé, pas à toute la souscription. Le rôle **Contributor ne peut pas attribuer de rôles RBAC**.

La personne invitée vérifie :

```bash
az account show --query "{subscription:name, tenant:tenantId}" -o json
az group show -n rg-projet-g2cc -o table
```

Voir le groupe prouve **la lecture**, pas le rôle Contributor à lui seul : confirmer son rôle dans **Access control (IAM)** et tester une action non destructive approuvée. Prévoir le délai de propagation RBAC.

## 3. Repli en cas d'échec

Si l'invitation externe Entra, la visibilité du groupe ou IAM sont bloquées par la politique de l'école, ne pas gaspiller de temps sur une impasse administrative :

- Le propriétaire exécute les opérations Azure en **partage d'écran** et conserve personnellement le contrôle du compte ; aucun mot de passe ni session n'est transféré.
- Les autres membres travaillent localement avec Docker, Azurite et Azure Functions Core Tools.
- Les déploiements sont confiés au workflow GitHub Actions avec identité OIDC fédérée.
- Garder des captures de l'échec et de la solution appliquée (en masquant les identifiants sensibles) ; vérifier au besoin les attentes de l'enseignante.

## 4. Rôles de projet / droits Azure

| Membre | Domaine | Droits Azure proposés |
|---|---|---|
| Aminata (R3) | Infrastructure et déploiement | Owner si son abonnement est retenu ; sinon Contributor au seul groupe |
| Gémima (coordination / appui R3 et R4) | Gestion du projet, appui à l'intégration Azure, budget en coordination avec Aminata et Omar | Owner si son abonnement est retenu ; sinon Contributor au seul groupe |
| Elias (R1) | Entraînement, FastAPI, tests | Pas d'accès direct Azure nécessaire au départ |
| Omar (pilote R4) | Dashboard, observabilité, KQL, métriques et alertes | Pas de droit Azure nécessaire pour préparer le code et les requêtes localement. Un accès RBAC limité peut être étudié si nécessaire et autorisé pour les manipulations Azure. |

**Nuance budgets :** un rôle Contributor au groupe n'assure pas la visibilité du crédit Azure for Students ni l'accès global à la facturation. Vérifier les permissions et restrictions Cost Management ; le propriétaire peut gérer le budget global. Des rôles supplémentaires de données Storage Blob/Queue peuvent être nécessaires pour certaines actions.

## 5. Règles de coexistence, sécurité et coûts

1. **Une création de ressources à la fois** : annoncer « je crée X » dans le groupe et coordonner l'exécution.
2. Créer les ressources prévues sous `rg-projet-g2cc`, dans une région compatible **après vérification** : `francecentral` reste proposée, **non garantie** par la politique Azure for Students. Vérifier **régions autorisées, quotas et disponibilité de Flex Consumption, Azure Container Apps et Cosmos DB** sur le compte retenu ; prévoir un essai de création **contrôlé et budgété** de Cosmos DB assez tôt une fois la souscription approuvée pour identifier les contraintes de capacité (sans créer de ressource dans cette PR). Inventorier aussi toute ressource créée automatiquement hors du groupe.
3. Déposer les commandes reproductibles, **commentées**, sous `infra/` (sans secrets) et documenter leur suppression.
4. Ne pas publier mot de passe, clé Azure, SAS, connection string, token ou fichier `.env` dans GitHub, WhatsApp, captures ou Word partagé.
5. Partager seulement les paramètres de connexion **non secrets** utiles : URL publique de l'API/site, nom du stockage, endpoint Cosmos DB. Cela n'accorde pas de droits sur leurs données.
6. Budget du projet : **25 USD maximum**, cible interne **moins de 5 USD**. Configurer les trois seuils d'alerte demandés : **20 %, 50 % et 80 %** du budget (soit 5, 12,50 et 20 USD pour un budget de 25 USD). Consigner les destinataires, le coût réel, la date des alertes et les captures. **Les alertes ne bloquent pas automatiquement les dépenses.**

## 6. Déploiement GitHub Actions + OIDC

- R1/R2 et R4 créent des branches, ouvrent des Pull Requests et obtiennent la revue exigée par la protection de `main`.
- **Choix du projet proposé par Aminata : une User-Assigned Managed Identity (UAMI)** avec *federated identity credential* pour GitHub Actions OIDC, conformément à son interprétation des consignes de cours. Ne retenir l'application/service principal Entra que si une validation explicite du professeur l'autorise. Aucune clé de service longue durée dans GitHub.
- L'identité de déploiement reçoit uniquement les rôles et scopes nécessaires, idéalement le RG, et pas l'abonnement entier.
- GitHub Actions doit disposer de `id-token: write` et `contents: read` pour le login OIDC.
- Préparer les identifiants de configuration GitHub Actions `AZURE_CLIENT_ID` (client ID de l'UAMI), `AZURE_TENANT_ID` et `AZURE_SUBSCRIPTION_ID`. Ce sont des **identifiants**, non des clés ou mots de passe ; ne pas les confondre avec des credentials, et leur appliquer les règles de confidentialité de l'équipe. Utiliser `azure/login` avec OIDC et la fédération GitHub restreinte à l'environnement et au workflow retenus.
- Ne pas créer d'identité ou d'attribution RBAC avant le choix de l'abonnement, la vérification du tenant et l'accord du titulaire des crédits.
- Configurer si disponible un environnement GitHub `production` avec *required reviewers* avant déploiement. **La revue de PR et l'approbation de déploiement sont deux validations distinctes.** Si la revue d'environnement n'est pas disponible (selon visibilité du dépôt, plan et paramètres), privilégier un **`workflow_dispatch` manuel** réservé aux comptes autorisés, et conserver les preuves de validation ; vérifier l'accessibilité effective de cette option avant d'annoncer un déploiement contrôlé.

## 7. Décisions encore nécessaires

- [ ] Solde/abonnement d'intégration retenu entre Gémima et Aminata.
- [ ] Vérification de la liste des régions autorisées, des quotas et de la capacité réelle des services (Functions Flex, Container Apps, Cosmos DB) ; planifier un essai de création Cosmos DB après validation du compte et du budget.
- [ ] Nom `rg-projet-g2cc` validé et groupe effectivement créé.
- [ ] Propriétaire effectif de l'abonnement et invité RBAC défini.
- [ ] Entra B2B autorisé ou repli partage d'écran établi.
- [ ] UAMI avec fédération OIDC et rôles minimaux configurés après choix de la souscription ; trois identifiants GitHub Actions enregistrés ; revue de l'environnement `production` ou repli `workflow_dispatch` testés.
- [ ] Budget et alertes de seuils **20 % / 50 % / 80 %** testés au périmètre autorisé.
- [ ] Captures, incidents, preuves et procédures de nettoyage consignés dans le Word collaboratif.

**Cette procédure est documentaire : aucune commande Azure n'a été exécutée en créant ce fichier.**

## Sources pour validation

- Microsoft Learn, [Azure roles for external users](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-external-users).
- Microsoft Learn, [Azure CLI role assignment](https://learn.microsoft.com/en-us/cli/azure/role/assignment).
- Microsoft Learn, [OIDC authentication from GitHub Actions](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect).
- Microsoft Learn, [Azure budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).

## 8. Mise en œuvre pour les quatre membres — 28 novembre 2026

Le groupe `rg-projet-g2cc` est déjà créé en France Central dans l'abonnement Azure for Students retenu par Gémima. Le budget, l'identité OIDC et le test de connexion en lecture seule ont été documentés. Les accès humains ci-dessous restent à vérifier et attribuer ; le rôle de l'identité managée ne donne pas de droits aux membres.

| Membre | Accès initial proposé (périmètre du seul groupe) | Complément éventuel |
|---|---|---|
| Gémima | Owner existant (à conserver, pas de nouveau rôle global) | Pilotage des droits et dépenses |
| Aminata | Contributor après accord de la propriétaire | Rôles de données Blob/Queue ciblés si nécessaires |
| Elias | Reader | Rôle ciblé sur Container Apps ou données de test uniquement si nécessaire |
| Omar | Reader + Monitoring Contributor si responsable des réglages/alertes | Accès aux logs et au conteneur statique $web, selon besoins réels |

Le rôle Contributor peut créer, modifier et supprimer des ressources et engendrer des coûts ; il ne donne pas le droit d'attribuer des rôles RBAC. Ne pas attribuer Owner, Contributor ou Billing Reader à l'échelle de l'abonnement à toute l'équipe. Commencer par les droits minimums et étendre uniquement si un test l'exige.

### Procédure depuis le portail (propriétaire)
1. Ouvrir https://portal.azure.com ; choisir le bon annuaire et l'abonnement d'intégration.
2. Ouvrir Groupes de ressources > rg-projet-g2cc > Contrôle d'accès (IAM) > Attributions de rôles. Vérifier les droits déjà existants pour éviter les doublons.
3. Ajouter > Ajouter une attribution de rôle ; choisir le rôle, puis Membres > Utilisateur, groupe ou principal de service > Sélectionner des membres. Utiliser l'adresse exacte du compte Microsoft/Azure de chaque membre.
4. Si le membre n'existe pas dans l'annuaire, l'inviter via Entra B2B si les politiques le permettent, puis lui attribuer le rôle dans le groupe. Il accepte l'invitation avec son propre compte. Si l'invitation est bloquée, noter l'erreur sans contourner la politique.
5. Vérifier + attribuer ; le membre bascule sur l'annuaire propriétaire dans le portail et confirme la visibilité du groupe et son accès IAM. Vérifier les rôles de données séparément, sans lancer de ressources.
6. Partager le lien du groupe en interne. Chaque membre ouvre son propre portail ou Cloud Shell ; les ressources sont communes mais les fichiers et sessions Cloud Shell ne sont pas automatiquement partagés.

### Règles opérationnelles
Les actions de création, suppression, modification réseau, augmentation de capacité et déploiement restent coordonnées et approuvées par la propriétaire. Maintenir les commutateurs de déploiement/publication désactivés tant que les validations ne sont pas réunies. Les droits humains ne prouvent ni l'éligibilité Free Tier ni une recette réelle. Noter date, membre, rôle, scope et vérification de lecture dans le Word partagé sans publier les adresses de compte, identifiants ni secrets. Retirer les accès temporaires après la soutenance et le nettoyage autorisé.

Sources : [Microsoft Learn — rôles externes](https://learn.microsoft.com/fr-fr/azure/role-based-access-control/role-assignments-external-users), [attribution de rôles](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-portal), [rôles Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/roles-permissions-security).
