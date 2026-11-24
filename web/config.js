// Configuration publique du tableau de bord (aucun secret ici).
// apiBaseUrl : URL de la Function App, sans "/" final, par exemple
//   "https://func-<equipe>.azurewebsites.net".
// Laisser vide pour utiliser les données simulées (sample-recent.json).
// Le paramètre d'URL ?mock=1 force aussi le mode simulé.
window.DSCC_CONFIG = {
  apiBaseUrl: "",
  recentPath: "/api/recent",
  refreshSeconds: 30,
  requestTimeoutMs: 10000,
};
