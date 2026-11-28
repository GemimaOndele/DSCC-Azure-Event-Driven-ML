const test = require("node:test");
const assert = require("node:assert/strict");
const {normalise, weightedProbability, mockRecent, modelVersions} = require("../../web/data.js");
const sample = require("../../web/sample-recent.json");
const row = {id:"synthetic-1",fileName:"test.csv",timestamp:"2026-11-26T19:00:00Z",
  rows:10,atRisk:2,avgChurnProbability:0.2,modelVersion:"1.1.0",durationMs:10,status:"ok"};
const envelope = (...results) => ({count:results.length,limit:20,results});
test("sample and empty responses accepted", () => {
  assert.equal(normalise(sample).length,8);
  assert.deepEqual(normalise(envelope()),[]);
});
for (const [field,value] of [
  ["timestamp","bad-date"],["rows",null],["rows","10"],["rows",-1],["rows",1.5],
  ["atRisk",11],["atRisk",-1],["avgChurnProbability",1.01],["avgChurnProbability",""],
  ["durationMs",-1],["durationMs",Infinity],["status","failed"]
]) {
  test("invalid "+field+" "+String(value)+" rejected", () => {
    assert.throws(() => normalise(envelope({...row,[field]:value})),/invalide/);
  });
}
test("wrong counts, limits and duplicate IDs rejected", () => {
  assert.throws(()=>normalise({...envelope(row),count:2}));
  assert.throws(()=>normalise({...envelope(row),limit:21}));
  assert.throws(()=>normalise(envelope(row,row)));
});
test("weighted probability excludes unknown rows; zero remains valid", () => {
  const items = normalise(envelope(row,{...row,id:"2",rows:90,avgChurnProbability:null}));
  assert.equal(weightedProbability(items),0.2);
  assert.equal(weightedProbability(normalise(envelope({...row,avgChurnProbability:0}))),0);
  assert.equal(weightedProbability(normalise(envelope({...row,avgChurnProbability:null}))),null);
});
test("mock generation is bounded after many refreshes", () => {
  let calls=0;
  const result=mockRecent(sample,1000000,i=>{calls++;return {...row,id:String(i)};});
  assert.equal(calls,20);
  assert.equal(result.count,20);
  assert.equal(normalise(result).length,20);
});

test("KPI uses actual returned versions, including historical results", () => {
  const items = normalise(envelope(row,{...row,id:"legacy",modelVersion:"1.0.0"}));
  assert.deepEqual(modelVersions(items),["1.1.0","1.0.0"]);
  assert.deepEqual(modelVersions(normalise(sample)),["1.1.0"]);
});
