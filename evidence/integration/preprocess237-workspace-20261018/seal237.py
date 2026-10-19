from pathlib import Path
import ast,difflib,hashlib,json,re
from datetime import datetime,timezone
w=Path(__file__).resolve().parent;parent=w.parent/'preprocess230-workspace-20261018';main=w.parents[2]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def pin(path):
 raw=path.read_bytes();return {'path':str(path.relative_to(w)) if path.is_relative_to(w) else str(path),'bytes':len(raw),'sha256':sha(raw)}
inputs=json.loads((w/'input-source-manifest237.json').read_text('utf-8'));before={x['path']:x for x in inputs['files']}
assert sha((parent/'freeze230.json').read_bytes())==inputs['parent230_freeze_sha256']
freeze230=json.loads((parent/'freeze230.json').read_text('utf-8'))
for entry in freeze230['files']:assert pin(parent/entry['path'])['sha256']==entry['after']['sha256'],entry['path']
for entry in freeze230['evidence']+freeze230['tests']:
 path=Path(entry['path']);path=path if path.is_absolute() else parent/path
 assert sha(path.read_bytes())==entry['sha256'],entry['path']
changed=[name for name,record in before.items() if sha((w/name).read_bytes())!=record['sha256']]
new=['tests/test_manifest_profile237.py']
allowed={'backend/app/ml/manifest_resource_profile.py','scripts/find_bare_targets173.py','scripts/propose_deficit_centers182.py','backend/app/data/candidates.py','backend/app/collection_status.py','backend/app/collection_priority_status.py'}
assert set(changed)==allowed,(changed,allowed)
excluded=['scripts/review_bare_targets179.py','scripts/collect_targeted_bare.py','backend/app/data/targeted_inventory_profile.py','tests/test_targeted_inventory_profile232.py','backend/app/data/targeted_inventory.py','backend/app/data/deficit_candidate_guard.py'];assert not set(changed+new)&set(excluded)
records=[];diff=[]
for name in sorted(changed+new):
 oldraw=None if name in new else (parent/name).read_bytes()
 if oldraw is not None:
  assert sha(oldraw)==before[name]['sha256'];archive=w/'baseline237-code'/name;archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(oldraw)
 raw=(w/name).read_bytes()
 records.append({'path':name,'before':None if oldraw is None else {'sha256':sha(oldraw),'bytes':len(oldraw)},'after':{'sha256':sha(raw),'bytes':len(raw)}})
 diff.extend(difflib.unified_diff([] if oldraw is None else oldraw.decode('utf-8-sig').splitlines(keepends=True),raw.decode('utf-8-sig').splitlines(keepends=True),fromfile='/dev/null' if oldraw is None else 'a/'+name,tofile='b/'+name))
exclusions=[]
for name in excluded:
 same=None if name not in before else sha((w/name).read_bytes())==before[name]['sha256']
 if same is not None:assert same
 exclusions.append({'path':name,'included':False,'isolated_matches_parent230':same})
(w/'patch237.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
manifest={'scope':'ISOLATED237_DELTA_OVER_FROZEN230_NOT_APPLIED_TO_MAIN','requires_parent230_freeze_sha256':inputs['parent230_freeze_sha256'],'files':records,'excluded_232_and_shared_files':exclusions,'main_written':0,'operating_data_read':0,'http':0,'collector':0,'live_qa':0}
(w/'patch237-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
log=w/'profile237-related-final.log';text=log.read_text('utf-8');match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert match and text.rstrip().endswith('OK')
tree=ast.parse((w/new[0]).read_text('utf-8'));focused=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body)
refs=['input-source-manifest237.json','input-test-code-supplement237.json','resource237-live-observation.json','profile237-focused-first.log','profile237-inherited-ui-check.log','profile237-related-fixture-missing-failed.log','profile237-related-final.log','patch237-manifest.json','patch237.diff','docs/ISOLATED237.md','seal237.py']
evidence=[pin(w/x) for x in refs]
evidence += [pin(main/'docs/implementation/237_complete_metadata_io_isolated.md'),pin(main/'docs/implementation/231_manifest_profile_followup230_review.md')]
assert evidence[-1]['sha256']=='6f47181a067963cd7f05d42e63a9c1a435c8754d05f773bbed230fb53d441e4f'
result={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'ISOLATED_IMPLEMENTATION_TESTED_SYNTHETIC_NOT_MERGED','parent230_freeze_sha256':inputs['parent230_freeze_sha256'],'parent230_all_frozen_code_evidence_logs_unchanged':True,'files':records,'evidence':evidence,'tests':{'related':int(match[1]),'seconds':float(match[2]),'focused237_included_not_additive':focused,'result':'PASS'},'excluded_232_and_shared_files':exclusions,'main_apply':False,'operating_data_read':0,'model_read':0,'ledger_read':0,'http':0,'collector':0,'live_qa':0,'limitations':['Temp synthetic and Mock evidence only; no real128MiB/3000row QA performance claim.','Resource observation is a single live sample; final peak RSS not measured.','Unclassified verified-file roles fail the explicit status observation closed.','Known synchronous RLock IO only; arbitrary async IO is not supported.','Published v1 cohort remains separate from v2 comparison and current source readiness.']}
(w/'freeze237.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'freeze237_sha256':sha((w/'freeze237.json').read_bytes()),'patch237_sha256':sha((w/'patch237.diff').read_bytes()),'manifest237_sha256':sha((w/'patch237-manifest.json').read_bytes()),'files':len(records),'related':int(match[1]),'seconds':float(match[2]),'focused237_included':focused},indent=2))
