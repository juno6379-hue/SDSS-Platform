type Row=Record<string,unknown>;
const row=(v:unknown):v is Row=>!!v&&typeof v==='object'&&!Array.isArray(v);
const count=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0;
const fraction=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1;
const sha=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export const progressSplits=['train','val','test'] as const;
export type ProgressSplit=typeof progressSplits[number];
export type ProgressRow={province:string;split:ProgressSplit;physical:number;eligible:number;yearCounts:Record<string,number>;cellGap:number};
export type BareObservation={pixels:number;ratio:number|null;contributingPatches:number};
export type CandidateProgress={sourceSha:string;eligible:number;splits:Record<ProgressSplit,number>;blockers:number;matchesCurrent:boolean;sourceReport:string;recordedAt:string;sceneConflicts:string[]};
export function parseCandidateProgress(value:unknown):CandidateProgress|undefined{
 if(!row(value)||value.available!==true)return;
 const fail=():never=>{throw new Error('후보 현황 응답 형식이 일치하지 않습니다.');};
 if(value.scope!=='PINNED_CANDIDATE_COHORT_NOT_AUTOMATIC_CURRENT_COLLECTION'||!sha(value.source_manifest_sha256)||value.ready_for_training!==false||value.scientific_accuracy_validated!==false||value.source_pins_match!==true||typeof value.source_matches_current_manifest!=='boolean'||!count(value.eligible_total)||!count(value.blocker_count)||!row(value.by_split)||!Array.isArray(value.scene_split_conflicts)||value.scene_split_conflicts.length!==0||typeof value.source_report!=='string'||value.source_report.length>512||/[\x00-\x1f\x7f]/.test(value.source_report)||typeof value.recorded_at!=='string'||!Number.isFinite(Date.parse(value.recorded_at)))fail();
 const sourceReport=value.source_report as string;if(/^(?:\/|\\|[A-Za-z]:|[a-z]+:)/i.test(sourceReport)||sourceReport.replaceAll('\\','/').split('/').some(p=>p==='..'||p==='.'||!p))fail();
 const bySplit=value.by_split as Row;if(Object.keys(bySplit).sort().join(',')!=='test,train,val'||progressSplits.some(s=>!count(bySplit[s]))||progressSplits.reduce((n,s)=>n+Number(bySplit[s]),0)!==value.eligible_total)fail();
 return {sourceSha:value.source_manifest_sha256 as string,eligible:value.eligible_total as number,splits:{train:bySplit.train as number,val:bySplit.val as number,test:bySplit.test as number},blockers:value.blocker_count as number,matchesCurrent:value.source_matches_current_manifest as boolean,sourceReport,recordedAt:value.recorded_at as string,sceneConflicts:[]};
}
export type CollectionProgressView={sourceSha:string;physical:number;eligible:number;ineligible:number;target:number;targetGap:number;cellFloor:number;cellGap:number;years:string[];rows:ProgressRow[];splits:Record<ProgressSplit,number>;minValid:number;minProvince:number;classFraction:number;minClassPatches:number;minPixelsPerPatch:number;minPixelsPerSplit:number;maxDominance:number;bare:Record<ProgressSplit,BareObservation>;sceneConflicts:string[]};
export function parseCollectionProgress(value:unknown):CollectionProgressView|undefined{
 if(!row(value)||value.available!==true)return;
 const fail=():never=>{throw new Error('수집 현황 응답의 집계·정책 형식을 확인할 수 없습니다.');};
 if(value.count_basis!=='manifest_quality_status'||!sha(value.source_manifest_sha256)||value.native_raster_reverified!==false||value.learning_ready!==false||value.scientific_accuracy_validated!==false)fail();
 const keys=['physical_total','eligible_total','ineligible_total','eligible_target','eligible_target_gap','cell_floor','cell_gap_total'];if(keys.some(key=>!count(value[key])))fail();
 if(Number(value.physical_total)!==Number(value.eligible_total)+Number(value.ineligible_total)||Number(value.eligible_target_gap)!==Math.max(0,Number(value.eligible_target)-Number(value.eligible_total)))fail();
 if(!fraction(value.minimum_valid_fraction)||!fraction(value.minimum_province_fraction)||!Array.isArray(value.rows)||value.rows.length!==6||!row(value.class_quality))fail();
 const rows:ProgressRow[]=[],splits={train:0,val:0,test:0},seen=new Set<string>();let years:string[]|undefined;
 for(const raw of value.rows as unknown[]){
  if(!row(raw))return fail();const item=raw;
  if(typeof item.province!=='string'||!/^[a-z_]{1,64}$/.test(item.province)||seen.has(item.province)||!progressSplits.includes(item.split as ProgressSplit)||!count(item.physical)||!count(item.eligible)||!count(item.cell_gap)||!row(item.year_counts))fail();
  const current=Object.keys(item.year_counts as Row).sort();if(current.length!==6||current.some(y=>!/^20[0-9]{2}$/.test(y))||current.some((y,i)=>i>0&&Number(y)!==Number(current[i-1])+1)||Object.values(item.year_counts as Row).some(n=>!count(n)))fail();
  if(years&&years.join(',')!==current.join(','))fail();years=current;seen.add(item.province as string);
  const yearCounts={...item.year_counts as Record<string,number>};if(Object.values(yearCounts).reduce((a,b)=>a+b,0)!==item.eligible||Number(item.eligible)>Number(item.physical)||Object.values(yearCounts).reduce((a,n)=>a+Math.max(0,Number(value.cell_floor)-n),0)!==item.cell_gap)fail();
  const split=item.split as ProgressSplit;splits[split]+=item.eligible as number;rows.push({province:item.province as string,split,physical:item.physical as number,eligible:item.eligible as number,yearCounts,cellGap:item.cell_gap as number});
 }
 if(rows.reduce((a,r)=>a+r.physical,0)!==value.physical_total||rows.reduce((a,r)=>a+r.eligible,0)!==value.eligible_total||rows.reduce((a,r)=>a+r.cellGap,0)!==value.cell_gap_total)fail();
 const c=value.class_quality as Row;if(!fraction(c.required_fraction)||!fraction(c.max_dominance)||!count(c.minimum_contributing_patches)||!count(c.minimum_pixels_per_contributing_patch)||!count(c.minimum_pixels_per_split)||!row(c.bare_by_split)||!Array.isArray(c.scene_split_conflicts)||c.scene_split_conflicts.length>20000||c.scene_split_conflicts.some(s=>typeof s!=='string'||s.length>512||/[\x00-\x1f\x7f]/.test(s)))fail();
 const bare={} as Record<ProgressSplit,BareObservation>;
 for(const split of progressSplits){const raw=(c.bare_by_split as Row)[split];if(!row(raw))return fail();const b=raw;if(!count(b.pixels)||!count(b.contributing_patches)||(b.ratio!==null&&!fraction(b.ratio)))fail();bare[split]={pixels:b.pixels as number,ratio:b.ratio as number|null,contributingPatches:b.contributing_patches as number};}
 return {sourceSha:value.source_manifest_sha256 as string,physical:value.physical_total as number,eligible:value.eligible_total as number,ineligible:value.ineligible_total as number,target:value.eligible_target as number,targetGap:value.eligible_target_gap as number,cellFloor:value.cell_floor as number,cellGap:value.cell_gap_total as number,years:years!,rows,splits,minValid:value.minimum_valid_fraction as number,minProvince:value.minimum_province_fraction as number,classFraction:c.required_fraction as number,minClassPatches:c.minimum_contributing_patches as number,minPixelsPerPatch:c.minimum_pixels_per_contributing_patch as number,minPixelsPerSplit:c.minimum_pixels_per_split as number,maxDominance:c.max_dominance as number,bare,sceneConflicts:[...c.scene_split_conflicts as string[]]};
}
export class CollectionProgressFlight{
 private generation=0;private pending=false;private controller?:AbortController;
 invalidate(){this.generation++;this.pending=false;this.controller?.abort();}
 async run(route:string,h:{route:()=>string;work:(signal:AbortSignal,live:()=>boolean)=>Promise<void>;error:()=>void;settled:()=>void}){
  if(this.pending)return;this.pending=true;const generation=this.generation,controller=new AbortController();this.controller=controller;
  const live=()=>generation===this.generation&&!controller.signal.aborted&&h.route()===route;
  try{await h.work(controller.signal,live);}catch{if(live())h.error();}finally{if(live()){this.pending=false;h.settled();}}
 }
}
