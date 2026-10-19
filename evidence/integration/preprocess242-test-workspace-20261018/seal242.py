from pathlib import Path
import difflib,hashlib,json,re
from datetime import datetime,timezone
w=Path(__file__).resolve().parent;parent=w.parent/'preprocess237-workspace-20261018';main=w.parents[2];shared=w/'evidence/shared-layout242/project'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def pin(path):
 raw=path.read_bytes();return {'path':str(path.relative_to(w)) if path.is_relative_to(w) else str(path),'bytes':len(raw),'sha256':sha(raw)}
inputs=json.loads((w/'input-source-manifest242.json').read_text('utf-8'));before={x['path']:x for x in inputs['files']}
assert sha((parent/'freeze237.json').read_bytes())==inputs['parent237_freeze_sha256']
pfreeze=json.loads((parent/'freeze237.json').read_text('utf-8'))
for entry in pfreeze['files']:assert sha((parent/entry['path']).read_bytes())==entry['after']['sha256']
for entry in pfreeze['evidence']:
 path=Path(entry['path']);path=path if path.is_absolute() else parent/path
 assert sha(path.read_bytes())==entry['sha256'],entry['path']
changed=[name for name,x in before.items() if sha((w/name).read_bytes())!=x['sha256']]
assert set(changed)=={'tests/test_manifest_profile228.py','tests/test_manifest_profile237.py'}
new=['tests/manifest_profile_baseline_fixtures.py','tests/test_manifest_profile242_portability.py']+[x.relative_to(w).as_posix() for x in sorted((w/'tests/fixtures/manifest_profile_baselines').iterdir()) if x.is_file()]
assert len(new)==7
paths=sorted(changed+new);diff=[];records=[]
for name in paths:
 oldraw=None if name in new else (parent/name).read_bytes();raw=(w/name).read_bytes()
 if oldraw is not None:
  assert sha(oldraw)==before[name]['sha256'];backup=w/'baseline242-tests'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(oldraw)
 assert (shared/name).read_bytes()==raw,name
 records.append({'path':name,'artifact_class':'PINNED_HISTORICAL_TEST_FIXTURE' if '/fixtures/' in name else 'TEST_SOURCE_OR_LOADER','before':None if oldraw is None else {'bytes':len(oldraw),'sha256':sha(oldraw)},'after':{'bytes':len(raw),'sha256':sha(raw)}})
 diff.extend(difflib.unified_diff([] if oldraw is None else oldraw.decode('utf-8-sig').splitlines(keepends=True),raw.decode('utf-8-sig').splitlines(keepends=True),fromfile='/dev/null' if oldraw is None else 'a/'+name,tofile='b/'+name))
(w/'patch242.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
bundle=sorted(set(paths+['tests/test_manifest_profile230.py']));assert len(bundle)==10
runtime=json.loads((w/'runtime18-unchanged242.json').read_text('utf-8'))
for entry in runtime['products']:
 for root in (w,shared):assert sha((root/entry['path']).read_bytes())==entry['237_sha256']
assert (w/'tests/test_manifest_profile230.py').read_bytes()==(parent/'tests/test_manifest_profile230.py').read_bytes()==(shared/'tests/test_manifest_profile230.py').read_bytes()
manifest={'scope':'TEST_ONLY_PORTABILITY_REVISION_RUNTIME237_EXACT_UNCHANGED','parent237_freeze_sha256':inputs['parent237_freeze_sha256'],'files':records,'root_main_test_bundle':[pin(w/x) for x in bundle],'runtime18_not_in_test_patch':runtime['products'],'test230_unchanged':True,'runtime_files_modified':0,'main_written':0,'operating_data_read':0,'http':0,'collector':0,'live_qa':0}
(w/'patch242-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
logs=[]
for name,layout in [('profile242-workspace-regression.log','ISOLATED_WORKSPACE'),('profile242-shared-layout-regression.log','SHARED_LAYOUT_WITHOUT_PARENT230_OR_BASELINE_CODE')]:
 path=w/name;text=path.read_text('utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert m and text.rstrip().endswith('OK')
 logs.append({**pin(path),'layout':layout,'tests':int(m[1]),'seconds':float(m[2]),'status':'PASS'})
refs=['input-source-manifest242.json','shared-layout242-manifest.json','runtime18-unchanged242.json','patch242-manifest.json','patch242.diff','docs/ISOLATED242.md','seal242.py'];evidence=[pin(w/x) for x in refs];evidence.append(pin(main/'docs/implementation/242_portable_profile_tests.md'))
result={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'TEST_ONLY_IMPLEMENTATION_TESTED_SYNTHETIC_NOT_APPLIED_TO_MAIN','parent237_freeze_sha256':inputs['parent237_freeze_sha256'],'parent237_frozen_products_evidence_unchanged':True,'files':records,'root_main_test_bundle_count':len(bundle),'root_main_test_bundle':[pin(w/x) for x in bundle],'evidence':evidence,'tests':logs,'runtime18_exact_unchanged':True,'test230_exact_unchanged':True,'main_written':0,'operating_data_read':0,'ledger_read':0,'model_read':0,'http':0,'collector':0,'live_qa':0,'limitations':['Same93-test suite run in two layouts; not186 distinct requirements.','No new128MiB load benchmark or actual rich3000-row QA.','Baseline portability only; dependency environment still uses existing .runtime libraries.','Runtime18 product application and operational verification remain separate Root decisions.']}
(w/'freeze242.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'freeze242_sha256':sha((w/'freeze242.json').read_bytes()),'patch242_sha256':sha((w/'patch242.diff').read_bytes()),'manifest242_sha256':sha((w/'patch242-manifest.json').read_bytes()),'test_only_delta':len(records),'test_bundle':len(bundle),'layouts':[(x['layout'],x['tests'],x['seconds']) for x in logs]},indent=2))
