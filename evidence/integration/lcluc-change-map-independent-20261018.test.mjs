import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {workflowChangePair,parseWorkflowChangeGeoJSON} from '../../frontend/src/lclucChangeMapAdapter.ts';
const fixture=JSON.parse(readFileSync(new URL('./lcluc-change-map-generated-fixture-20261018.json',import.meta.url),'utf8'));
const clone=v=>structuredClone(v);
const selected=pair=>workflowChangePair(fixture.receipt,fixture.report,pair);

test('independent real CPU three-year results select nonempty and empty without mutating proof',()=>{
 const before=JSON.stringify(fixture);
 for(const [pair,count,area] of [['2020-2021',1,25600],['2021-2022',0,0],['2020-2022',1,25600]]){
  const choice=selected(pair),view=parseWorkflowChangeGeoJSON(fixture.geojson[pair],choice);
  assert.equal(view.featureCount,count);assert.equal(view.empty,count===0);
  assert.equal(choice.changedAreaM2,area);assert.equal(choice.validPixels,256);
  assert.equal(view.bounds===null,count===0);
 }
 assert.equal(JSON.stringify(fixture),before);
});
test('independent year pair and artifact path rebinding are rejected',()=>{
 for(const mutate of [r=>r.changes['2020-2021'].from_year=2019,r=>r.changes['2020-2021'].geojson_path=r.changes['2021-2022'].geojson_path]){
  const report=clone(fixture.report);mutate(report);
  assert.throws(()=>workflowChangePair(fixture.receipt,report,'2020-2021'));
 }
 assert.throws(()=>selected('2022-2020'));assert.throws(()=>selected('2020-2025'));
});
test('independent duplicate receipt artifact and external namespace reject before map selection',()=>{
 const receipt=clone(fixture.receipt);receipt.artifacts.push(clone(receipt.artifacts[0]));
 assert.throws(()=>workflowChangePair(receipt,fixture.report,'2020-2021'));
 const report=clone(fixture.report);report.changes['2020-2021'].geojson_path='https://example.invalid/changes.geojson';
 assert.throws(()=>workflowChangePair(fixture.receipt,report,'2020-2021'));
});
test('independent nonempty coordinates are bounded and detached from untrusted input',()=>{
 const geo=clone(fixture.geojson['2020-2021']),view=parseWorkflowChangeGeoJSON(geo,selected('2020-2021'));
 geo.features[0].geometry.coordinates[0][0][0]=180;
 assert.notEqual(view.geojson.features[0].geometry.coordinates[0][0][0],180);
 assert.equal(view.vertexCount,5);assert.equal(view.geojson.features[0].properties.transition_code,11);
 for(const position of [[181,0],[0,91],[0,NaN],[0,0,1]]){
  const changed=clone(fixture.geojson['2020-2021']);changed.features[0].geometry.coordinates[0][0]=position;
  assert.throws(()=>parseWorkflowChangeGeoJSON(changed,selected('2020-2021')));
 }
});
test('independent rendering collection excludes inline CRS or unsupported features and metadata mismatch',()=>{
 const choice=selected('2020-2021');
 for(const mutate of [g=>g.crs={type:'name',properties:{name:'EPSG:3857'}},g=>g.features[0].geometry={type:'GeometryCollection',geometries:[]},g=>g.features[0].properties.from_class=2]){
  const geo=clone(fixture.geojson['2020-2021']);mutate(geo);assert.throws(()=>parseWorkflowChangeGeoJSON(geo,choice));
 }
 assert.throws(()=>parseWorkflowChangeGeoJSON(fixture.geojson['2021-2022'],choice));
});
test('independent dateline spanning preview rejects and empty does not invent bounds',()=>{
 const geo=clone(fixture.geojson['2020-2021']);geo.features[0].geometry.coordinates=[[[179,0],[-179,0],[-179,1],[179,0]]];
 assert.throws(()=>parseWorkflowChangeGeoJSON(geo,selected('2020-2021')));
 const empty=parseWorkflowChangeGeoJSON(fixture.geojson['2021-2022'],selected('2021-2022'));
 assert.deepEqual(empty.geojson,{type:'FeatureCollection',features:[]});assert.equal(empty.bounds,null);
});
