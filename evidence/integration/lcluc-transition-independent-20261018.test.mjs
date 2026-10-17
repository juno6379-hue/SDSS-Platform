import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {workflowTransitionStats,WORKFLOW_CLASS_COLORS} from '../../frontend/src/lclucTransitionAdapter.ts';
const proof=JSON.parse(readFileSync(new URL('./lcluc-transition-generated-fixture-20261018.json',import.meta.url),'utf8'));
const clone=v=>structuredClone(v),pair='2020-2021';
const read=(report=proof.report,p=pair)=>workflowTransitionStats(proof.receipt,report,p);

test('independent actual CPU three-year matrix direction and net area match known threshold network',()=>{
 const stats=read();assert.equal(stats.transitionPixels[1][2],256);
 assert.equal(stats.classes[1].beforePixels,256);assert.equal(stats.classes[1].afterPixels,0);
 assert.equal(stats.classes[2].beforePixels,0);assert.equal(stats.classes[2].afterPixels,256);
 assert.equal(stats.classes[1].netAreaM2,-25600);assert.equal(stats.classes[2].netAreaM2,25600);
 assert.equal(stats.changedAreaM2/10000,2.56);assert.equal(stats.changeRate,1);
 const unchanged=read(proof.report,'2021-2022');assert.equal(unchanged.transitionPixels[2][2],256);
 assert.equal(unchanged.changedAreaM2,0);assert.equal(unchanged.changeRate,0);
});
test('independent area magnitude never loosens dimensionless change rate check',()=>{
 const report=clone(proof.report),c=report.changes[pair],scale=1e8;
 c.transition_area_m2=c.transition_area_m2.map(row=>row.map(n=>n*scale));
 c.total_area_m2*=scale;c.changed_area_m2*=scale;c.class_net_area_m2=c.class_net_area_m2.map(n=>n*scale);
 assert.equal(read(report).changeRate,1);c.change_rate=.5;
 assert.throws(()=>read(report));
});
test('independent offdiagonal and marginal corruption reject without repairing report',()=>{
 for(const mutate of [c=>c.transition_pixels[1][2]--,c=>c.transition_area_m2[1][2]++,c=>c.class_net_area_m2[1]=0,c=>c.changed_area_m2=0]){
  const report=clone(proof.report);mutate(report.changes[pair]);const before=JSON.stringify(report);
  assert.throws(()=>read(report));assert.equal(JSON.stringify(report),before);
 }
});
test('independent class ordering binds labels but duplicate literal labels retain numeric IDs',()=>{
 const changed=clone(proof.report);changed.changes[pair].class_names.reverse();assert.throws(()=>read(changed));
 const duplicate=clone(proof.report);duplicate.class_names[1]=duplicate.class_names[2];duplicate.changes[pair].class_names[1]=duplicate.class_names[2];
 const s=read(duplicate);assert.equal(s.classes[1].name,s.classes[2].name);assert.notEqual(s.classes[1].id,s.classes[2].id);
 const control=clone(proof.report);control.class_names[1]='bad\nlabel';control.changes[pair].class_names[1]='bad\nlabel';assert.throws(()=>read(control));
});
test('independent zero valid pixels require null rate, not a fabricated zero percentage',()=>{
 const report=clone(proof.report),c=report.changes[pair];
 c.transition_pixels=Array.from({length:9},()=>Array(9).fill(0));c.transition_area_m2=Array.from({length:9},()=>Array(9).fill(0));
 c.valid_pixels=0;c.total_area_m2=0;c.changed_area_m2=0;c.change_rate=null;c.class_net_area_m2=Array(9).fill(0);
 assert.equal(read(report).changeRate,null);c.change_rate=0;assert.throws(()=>read(report));
});
test('independent numeric cell types and sparse matrices reject',()=>{
 for(const value of [true,-1,.5,Number.MAX_SAFE_INTEGER+1,NaN,Infinity]){
  const report=clone(proof.report);report.changes[pair].transition_pixels[1][2]=value;assert.throws(()=>read(report));
 }
 const sparse=clone(proof.report);delete sparse.changes[pair].transition_area_m2[1][2];assert.throws(()=>read(sparse));
});
test('independent detached display output and immutable palette cannot modify source proof',()=>{
 const before=JSON.stringify(proof),s=read();s.classes[1].name='local-only';s.transitionPixels[1][2]=0;s.transitionAreaM2[1][2]=0;
 assert.equal(JSON.stringify(proof),before);assert.equal(WORKFLOW_CLASS_COLORS.length,9);assert.equal(Object.isFrozen(WORKFLOW_CLASS_COLORS),true);
});
test('independent vector subset is never used as full raster statistical basis',()=>{
 const report=clone(proof.report);report.changes[pair].statistics_basis='vector_only';assert.throws(()=>read(report));
 const method=clone(proof.report);method.changes[pair].area_method='geographic_cell_area_m2';assert.throws(()=>read(method));
});
