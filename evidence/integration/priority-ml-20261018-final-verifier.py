"""Independent post-QA row partition/token overlap and actual file SHA checks."""
import hashlib,json,time
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
PREFIX=ROOT/'evidence/integration/priority-ml-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
summary=load(Path(str(PREFIX)+'-summary.json'))
start=time.monotonic()
outputs=summary['outputs']
assert all(sha(ROOT/p)==v['sha256'] and (ROOT/p).stat().st_size==v['bytes'] for p,v in outputs.items())
source_path=ROOT/'data/priority-ml-snapshot-20261018/annual-window-report.json'
source=load(source_path);candidate=load(ROOT/'data/priority-ml-stage-20261018/candidate.json')
report=load(ROOT/'data/priority-ml-readiness-20261018/readiness.json')
indexes=candidate['lineage']['source_row_indexes'];retained=[source['scenes'][i] for i in indexes]
assert retained==candidate['scenes']
assert set(indexes).isdisjoint(summary['excluded_row_indexes'])
assert set(indexes)|set(summary['excluded_row_indexes'])==set(range(len(source['scenes'])))
assert sha(source_path)==summary['raw_source_snapshot_sha256']
tokens=defaultdict(set)
for row in candidate['scenes']:
    split=report['policy']['province_splits'][row['province']]
    for token in ['source:'+row['scene_id'],'source:'+row['source_group'],'image:'+row['patch_sha256']['image']]:tokens[token].add(split)
conflicts=[k for k,v in tokens.items() if len(v)>1];assert not conflicts
file_mismatches=[]
for item in report['verified_files']:
    path=ROOT/'data'/item['path']
    if sha(path)!=item['sha256']:file_mismatches.append(item['path'])
assert not file_mismatches
result={'status':'FINAL_CANDIDATE_ROW_AND_FILE_PINS_MATCH','seconds':round(time.monotonic()-start,3),'source_sha256':sha(source_path),'candidate_sha256':sha(ROOT/'data/priority-ml-stage-20261018/candidate.json'),'qa_report_sha256':sha(ROOT/'data/priority-ml-readiness-20261018/readiness.json'),'retained_rows_exact':True,'partition_complete':True,'candidate_source_identity_cross_split_conflicts':len(conflicts),'verified_file_records':len(report['verified_files']),'file_sha_mismatches':file_mismatches,'all_output_pins_match':True,'training_executed':False,'scientific_accuracy_validated':False,'scope':'DECLARED_SOURCE_IDENTITIES_AND_READINESS_VERIFIED_FILES_NOT_INDEPENDENT_GROUND_TRUTH'}
with Path(str(PREFIX)+'-final-verification.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(result,ensure_ascii=True),flush=True)
