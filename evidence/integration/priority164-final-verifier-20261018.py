"""Independent final row partition, cross-split identity and output/file pin audit."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time
ROOT=Path(__file__).resolve().parents[2]
work=ROOT/'data/priority164-cohort-20261018'
evidence=ROOT/'evidence/integration'
summary_path=evidence/'priority164-cohort-20261018/summary.json'
def load(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
start=time.monotonic();summary=load(summary_path)
assert summary['status']=='PINNED_CANDIDATE_QA_COMPLETED'
assert all(sha(Path(p))==r['sha256'] and Path(p).stat().st_size==r['bytes'] for p,r in summary['outputs'].items())
source=load(work/'source.json');candidate=load(work/'stage/candidate.json');report=load(work/'qa/readiness.json')
indexes=candidate['lineage']['source_row_indexes']
assert candidate['scenes']==[source['scenes'][i] for i in indexes]
plan=load(evidence/'priority164-cohort-20261018/split-plan.json')
assert set(indexes).isdisjoint(plan['excluded_row_indexes'])
assert set(indexes)|set(plan['excluded_row_indexes'])==set(range(len(source['scenes'])))
tokens=defaultdict(set)
for row in candidate['scenes']:
    split=report['policy']['province_splits'][row['province']]
    for token in ['source:'+row['scene_id'],'source:'+row['source_group'],'image:'+row['patch_sha256']['image']]:tokens[token].add(split)
conflicts=[k for k,v in tokens.items() if len(v)>1];assert not conflicts
mismatches=[r['path'] for r in report['verified_files'] if sha(ROOT/'data'/r['path'])!=r['sha256']]
assert not mismatches
result={'status':'FINAL_PRIORITY164_ROWS_AND_FILE_PINS_MATCH','seconds':round(time.monotonic()-start,3),'source_sha256':sha(work/'source.json'),'candidate_sha256':sha(work/'stage/candidate.json'),'qa_report_sha256':sha(work/'qa/readiness.json'),'source_rows':len(source['scenes']),'candidate_rows':len(candidate['scenes']),'excluded_rows':len(plan['excluded_row_indexes']),'exact_retained_rows':True,'partition_complete':True,'cross_split_source_identity_conflicts':len(conflicts),'verified_file_records':len(report['verified_files']),'file_mismatches':mismatches,'connectivity_capture_status':report['connectivity_diagnostics']['capture_status'],'scope':'PINNED_COHORT_ONLY_NOT_LATER_COLLECTION_OR_INDEPENDENT_LABELS','training_executed':False,'scientific_accuracy_validated':False}
with (evidence/'priority164-final-verification-20261018.json').open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(result,ensure_ascii=True),flush=True)
