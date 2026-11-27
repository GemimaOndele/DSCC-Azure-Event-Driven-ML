/* Pure data validation for both browser and Node test runner. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DSCC_DATA = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function fail() { throw new Error("Réponse /api/recent invalide ; dernières données conservées."); }
  function count(n) { return Number.isSafeInteger(n) && n >= 0; }
  function text(s) { return typeof s === "string" && s.trim().length > 0; }
  function optionalNumber(n, max) {
    if (n === null || n === undefined) return null;
    if (typeof n !== "number" || !Number.isFinite(n) || n < 0 || n > max) fail();
    return n;
  }
  function normalise(payload) {
    if (!payload || !Array.isArray(payload.results) || !count(payload.count) ||
        !Number.isSafeInteger(payload.limit) || payload.limit < 1 || payload.limit > 20 ||
        payload.count !== payload.results.length || payload.count > payload.limit) fail();
    const seen = new Set();
    return payload.results.map(item => {
      if (!item || typeof item !== "object" || !text(item.id) || seen.has(item.id) ||
          !text(item.fileName) || !text(item.modelVersion) || item.status !== "ok" ||
          !count(item.rows) || !count(item.atRisk) || item.atRisk > item.rows ||
          !text(item.timestamp) || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(item.timestamp)) fail();
      const timestamp = new Date(item.timestamp);
      if (!Number.isFinite(timestamp.getTime())) fail();
      seen.add(item.id);
      return {
        id: item.id, fileName: item.fileName, timestamp,
        rows: item.rows, atRisk: item.atRisk,
        avgChurnProbability: optionalNumber(item.avgChurnProbability, 1),
        modelVersion: item.modelVersion,
        durationMs: optionalNumber(item.durationMs, Number.MAX_SAFE_INTEGER),
        status: item.status,
      };
    }).sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }
  function weightedProbability(items) {
    const known = items.filter(item => item.avgChurnProbability !== null);
    const total = known.reduce((sum, item) => sum + item.rows, 0);
    return total ? known.reduce((sum, item) => sum + item.avgChurnProbability * item.rows, 0) / total : null;
  }
  function mockRecent(sample, tick, makeResult) {
    // Limit generation work and output independently of number of refreshes.
    normalise(sample);
    const items = sample.results.slice();
    const start = Math.max(1, tick - sample.limit + 1);
    for (let i = start; i <= tick; i += 1) items.unshift(makeResult(i));
    const results = items.slice(0, sample.limit);
    return { count: results.length, limit: sample.limit, results };
  }
  function modelVersions(items) { return [...new Set(items.map(item => item.modelVersion))]; }
  return { normalise, weightedProbability, mockRecent, modelVersions };
});
