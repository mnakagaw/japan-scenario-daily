// No browser or third-party packages: execute the real arithmetic helpers.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = {document:{documentElement:{classList:{add(){}}},querySelector(){return null;},querySelectorAll(){return [];}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('assets/app.js','utf8')+'\nglobalThis.testAPI={difference,formatP,changeMarkup,escapeHTML};',context);
const {difference,formatP,changeMarkup,escapeHTML}=context.testAPI;
const date={series_id:'one',deadline:'2026-11-03T23:59:59-05:00',forecast_start:'2026-09-13T11:36:53+09:00'};
const a={p_final:.4,definition_version:1,target:'same question'}, b={p_final:.45,definition_version:1,target:'same question'};
assert.equal(difference(a,b,date,date),5);
assert.equal(difference(b,a,date,date),-5);
assert.equal(difference(a,a,date,date),0);
assert.equal(difference({...a,p_final:null},b,date,date),null);
assert.equal(difference(a,{...b,definition_version:2},date,date),null);
assert.equal(difference(a,b,date,{...date,series_id:'two'}),null);
assert.equal(difference(a,b,date,{...date,deadline:'2027-01-01T00:00:00Z'}),null);
assert.equal(formatP(null),'未設定');
assert.equal(formatP(0),'0%');
assert.match(changeMarkup(null),/比較不可/);
assert.doesNotMatch(changeMarkup(null),/0 pt/);
assert.equal(escapeHTML('<script>'),'&lt;script&gt;');
console.log('PASS: real client comparison helpers, missing values, changed definitions, output escaping.');

assert.equal(difference(a,{...b,target:'different question'},date,date),null);
assert.equal(difference(a,b,date,{...date,deadline:'2026-11-04T13:59:59+09:00'}),5);
assert.equal(difference(a,b,date,{...date,forecast_start:'2026-09-14T11:36:53+09:00'}),null);
