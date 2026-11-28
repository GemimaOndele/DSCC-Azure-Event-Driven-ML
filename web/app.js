// Tableau de bord DSCC — lit GET /api/recent et s'actualise toutes les 30 s.
// Contrat (functions/src/service.py, #6) :
//   { count, limit, results: [{ id, fileName, timestamp, rows, atRisk,
//     avgChurnProbability, modelVersion, durationMs, status }] }
(function () {
  "use strict";

  const config = Object.assign(
    { apiBaseUrl: "", recentPath: "/api/recent", refreshSeconds: 30, requestTimeoutMs: 10000 },
    window.DSCC_CONFIG || {}
  );
  const params = new URLSearchParams(window.location.search);
  const mockMode = params.get("mock") === "1" || !config.apiBaseUrl;
  const refreshMs = Math.max(5, Number(config.refreshSeconds) || 30) * 1000;

  const $ = (id) => document.getElementById(id);
  const numberFmt = new Intl.NumberFormat("fr-FR");
  const percentFmt = new Intl.NumberFormat("fr-FR", { style: "percent", maximumFractionDigits: 1 });
  const dateFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });

  let chart = null;
  let nextRefreshAt = 0;
  let inFlight = false;
  let mockTick = 0;

  // ---------- Récupération des données ----------

  async function fetchJson(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
    try {
      const response = await fetch(url, {
        signal: controller.signal,
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} sur ${url}`);
      }
      return await response.json();
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error(`Délai dépassé (${config.requestTimeoutMs} ms) sur ${url}`);
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  async function loadRecent() {
    if (!mockMode) {
      return fetchJson(config.apiBaseUrl.replace(/\/$/, "") + config.recentPath);
    }
    // Mode simulé : jeu d'exemple + un fichier fictif ajouté à chaque
    // actualisation, pour montrer le rafraîchissement sans Azure.
    const sample = await fetchJson("sample-recent.json");
    return window.DSCC_DATA.mockRecent(sample, mockTick++, simulatedResult);
  }

  function simulatedResult(index) {
    const rows = 40 + ((index * 37) % 80);
    const atRisk = Math.round(rows * (0.18 + ((index * 13) % 20) / 100));
    return {
      id: `simulated-${index}`,
      fileName: `simulated_batch_${String(index).padStart(3, "0")}.csv`,
      timestamp: new Date(Date.now() - (mockTick - index) * refreshMs).toISOString(),
      rows,
      atRisk,
      avgChurnProbability: Math.min(0.95, atRisk / rows + 0.04),
      modelVersion: "1.1.0",
      durationMs: 600 + ((index * 211) % 1400),
      status: "ok",
    };
  }

  // ---------- Normalisation et agrégats ----------

  const normalise = window.DSCC_DATA.normalise;

  function sum(items, key) {
    return items.reduce((total, item) => total + (item[key] ?? 0), 0);
  }

  // ---------- Rendu ----------

  function renderKpis(items) {
    const rows = sum(items, "rows");
    const atRisk = sum(items, "atRisk");
    // Moyenne pondérée par le nombre de clients de chaque fichier.
    const weighted = window.DSCC_DATA.weightedProbability(items);
    const durations = items.map((item) => item.durationMs).filter((d) => d !== null);
    const versions = window.DSCC_DATA.modelVersions(items);

    $("kpi-files").textContent = numberFmt.format(items.length);
    $("kpi-rows").textContent = numberFmt.format(rows);
    $("kpi-risk").textContent = numberFmt.format(atRisk);
    $("kpi-risk-rate").textContent = rows ? `${percentFmt.format(atRisk / rows)} des clients` : "";
    $("kpi-proba").textContent = weighted !== null ? percentFmt.format(weighted) : "—";
    $("kpi-duration").textContent = durations.length
      ? `${numberFmt.format(Math.round(durations.reduce((a, b) => a + b, 0) / durations.length))} ms`
      : "—";
    $("kpi-model").textContent = versions.length ? versions.join(", ") : "—";
  }

  function renderTable(items) {
    const body = $("results-body");
    body.replaceChildren();
    $("empty-state").hidden = items.length > 0;

    for (const item of items) {
      const tr = document.createElement("tr");
      const riskRate = item.rows ? item.atRisk / item.rows : 0;
      const cells = [
        [item.timestamp ? dateFmt.format(item.timestamp) : "—"],
        [item.fileName, "file"],
        [item.rows === null ? "—" : numberFmt.format(item.rows), "num"],
        [item.atRisk === null ? "—" : numberFmt.format(item.atRisk), riskRate >= 0.3 ? "num risk-high" : "num"],
        [item.avgChurnProbability === null ? "—" : percentFmt.format(item.avgChurnProbability), "num"],
        [item.durationMs === null ? "—" : `${numberFmt.format(item.durationMs)} ms`, "num"],
        [item.modelVersion],
        [item.status, item.status === "ok" ? "status-ok" : "status-ko"],
      ];
      for (const [text, className] of cells) {
        const td = document.createElement("td");
        td.textContent = text; // textContent : aucun HTML injecté depuis l'API.
        if (className) td.className = className;
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
  }

  function renderChart(items) {
    if (typeof window.Chart === "undefined") {
      return; // CDN indisponible : le tableau et les KPI restent utilisables.
    }
    const ordered = items.slice().reverse(); // chronologique, de gauche à droite
    const labels = ordered.map((item) => item.fileName);
    const atRisk = ordered.map((item) => item.atRisk ?? 0);
    const safe = ordered.map((item) => Math.max(0, (item.rows ?? 0) - (item.atRisk ?? 0)));
    const proba = ordered.map((item) =>
      item.avgChurnProbability === null ? null : Math.round(item.avgChurnProbability * 1000) / 10
    );

    if (!chart) {
      const styles = getComputedStyle(document.documentElement);
      const risk = styles.getPropertyValue("--risk").trim();
      const ok = styles.getPropertyValue("--ok").trim();
      const line = styles.getPropertyValue("--accent").trim();
      window.Chart.defaults.color = styles.getPropertyValue("--muted").trim();
      window.Chart.defaults.borderColor = styles.getPropertyValue("--border").trim();
      chart = new window.Chart($("risk-chart"), {
        data: {
          labels,
          datasets: [
            { type: "bar", label: "À risque", data: atRisk, backgroundColor: risk, stack: "clients", yAxisID: "y" },
            { type: "bar", label: "Non à risque", data: safe, backgroundColor: ok, stack: "clients", yAxisID: "y" },
            {
              type: "line", label: "Probabilité moyenne (%)", data: proba, borderColor: line,
              backgroundColor: line, yAxisID: "y1", tension: 0.25, pointRadius: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { stacked: true, ticks: { autoSkip: true, maxRotation: 45 } },
            y: { stacked: true, beginAtZero: true, title: { display: true, text: "Clients" } },
            y1: {
              position: "right", min: 0, max: 100, grid: { drawOnChartArea: false },
              title: { display: true, text: "Probabilité (%)" },
            },
          },
        },
      });
      return;
    }
    chart.data.labels = labels;
    chart.data.datasets[0].data = atRisk;
    chart.data.datasets[1].data = safe;
    chart.data.datasets[2].data = proba;
    chart.update();
  }

  function showError(message) {
    const banner = $("error-banner");
    banner.textContent = message
      ? `Impossible de récupérer les données : ${message}. Nouvel essai à la prochaine actualisation.`
      : "";
    banner.hidden = !message;
  }

  // ---------- Boucle d'actualisation ----------

  async function refresh() {
    if (inFlight) return;
    inFlight = true;
    $("refresh-now").disabled = true;
    try {
      const items = normalise(await loadRecent());
      renderKpis(items);
      renderTable(items);
      renderChart(items);
      showError("");
      $("last-update").textContent = `Actualisé à ${new Date().toLocaleTimeString("fr-FR")}`;
    } catch (error) {
      // On garde les dernières données affichées et on signale l'erreur.
      showError(error.message || String(error));
    } finally {
      inFlight = false;
      $("refresh-now").disabled = false;
      nextRefreshAt = Date.now() + refreshMs;
    }
  }

  function tickCountdown() {
    const remaining = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000));
    $("countdown").textContent = nextRefreshAt ? `prochaine dans ${remaining} s` : "";
    if (nextRefreshAt && Date.now() >= nextRefreshAt && !inFlight && !document.hidden) {
      refresh();
    }
  }

  function init() {
    const badge = $("source-badge");
    badge.textContent = mockMode ? "Données simulées" : "Données Azure";
    badge.classList.add(mockMode ? "badge-mock" : "badge-live");
    $("refresh-seconds").textContent = String(refreshMs / 1000);
    $("refresh-now").addEventListener("click", refresh);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && Date.now() >= nextRefreshAt) refresh();
    });
    refresh();
    setInterval(tickCountdown, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
