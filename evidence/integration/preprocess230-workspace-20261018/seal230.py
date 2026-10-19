from pathlib import Path
import json,hashlib,difflib,re
from datetime import datetime,timezone
w=Path(__file__).resolve().parent;p=w.parent/'preprocess228-workspace-20261018';main=w.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(path):
 raw=path.read_bytes();return {'path':str(path.relative_to(w)) if path.is_relative_to(w) else str(path),'bytes':len(raw),'sha256':sha(raw)}
index=json.loads((w/'input-source-manifest.json').read_text('utf-8'));old={x['path']:x for x in index['files']}
paths=[x for x in old if (w/x).exists() and sha((w/x).read_bytes())!=old[x]['sha256']]
paths+=['backend/app/collection_source_profile.py','tests/test_manifest_profile230.py']
excluded=['scripts/review_bare_targets179.py','scripts/collect_targeted_bare.py','backend/app/data/targeted_inventory_profile.py','tests/test_targeted_inventory_profile232.py','backend/app/data/targeted_inventory.py','backend/app/data/deficit_candidate_guard.py']
assert not set(paths)&set(excluded)
files=[];diff=[]
for name in paths:
 before=(p/name).read_bytes() if name in old else None
 if before is not None:
  assert sha(before)==old[name]['sha256'],name
  archive=w/'baseline230-code'/name;archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(before)
 after=(w/name).read_bytes()
 files.append({'path':name,'before':None if before is None else {'sha256':sha(before),'bytes':len(before)},'after':{'sha256':sha(after),'bytes':len(after)}})
 diff.extend(difflib.unified_diff([] if before is None else before.decode('utf-8-sig').splitlines(keepends=True),after.decode('utf-8-sig').splitlines(keepends=True),fromfile='/dev/null' if before is None else 'a/'+name,tofile='b/'+name))
assert sha((p/'freeze228.json').read_bytes())==index['parent228_freeze_sha256']
parent=json.loads((p/'freeze228.json').read_text('utf-8'))
for x in parent['patch_files']:assert sha((p/x['path']).read_bytes())==x['after']['sha256'],x['path']
excludeproof=[]
for name in excluded:
 entry={'path':name,'included':False}
 if name in old:
  entry['isolated_matches_parent228']=sha((w/name).read_bytes())==old[name]['sha256'];assert entry['isolated_matches_parent228']
 else:entry['isolated_copy_present']=(w/name).exists()
 excludeproof.append(entry)
(w/'patch230.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
manifest={'scope':'ISOLATED230_DELTA_OVER_FROZEN228_NOT_APPLIED_TO_MAIN','requires_parent228_freeze_sha256':index['parent228_freeze_sha256'],'files':files,'excluded_232_and_shared_files':excludeproof,'main_products_written':0,'operating_data_reads':0,'http':0,'collector':0,'live_qa':0}
(w/'patch230-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
logs=[]
for name in ['profile230-focused-final.log','profile230-related-176-before-cli-output-final.log','profile230-final-cli-output-check.log']:
 path=w/name;text=path.read_text('utf-8');match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text);assert match and text.rstrip().endswith('OK'),name
 logs.append({**pin(path),'tests':int(match[1]),'seconds':float(match[2]),'status':'PASS','revision_scope':'FINAL_CODE' if name=='profile230-final-cli-output-check.log' else 'BEFORE_FINAL_173_182_OUTPUT_ACCOUNTING'})
extra=[pin(w/x) for x in ['patch230.diff','patch230-manifest.json','input-source-manifest.json','docs/ISOLATED230.md','seal230.py']]
extra.append(pin(main/'docs/implementation/230_explicit_source_profile_and_resource_guards_isolated.md'))
result={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'ISOLATED_IMPLEMENTATION_TESTED_SYNTHETIC_NOT_MERGED','main_apply':False,'operating_reads':0,'http':0,'collector':0,'live_qa':0,'parent228_freeze_sha256':index['parent228_freeze_sha256'],'parent228_unchanged':True,'files':files,'evidence':extra,'tests':logs,'excluded_232_and_shared_files':excludeproof,'limits':{'source_candidate_json':134217728,'scenes_plus_history':3000,'depth':32,'tree_visits':4000000,'local_metadata_io':17179869184,'label_raster_header_each_unchanged':67108864,'remote_additional_unchanged':4294967296},'limitations':['No real rich128MiB/3000-row QA performance was measured.','Inherited228 whitespace benchmark remains historical only.','176 regression predates the final narrow173/182 output-accounting connection; final targeted regression checks that connection plus shared profile.','Known synchronous shared-budget I/O is locked; arbitrary async await inside a transaction is unsupported.','Budget card streams source SHA and does not establish row-quality readiness.','No shared product application or server/frontend runtime change.']}
(w/'freeze230.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'freeze230_sha256':sha((w/'freeze230.json').read_bytes()),'patch230_sha256':sha((w/'patch230.diff').read_bytes()),'manifest_sha256':sha((w/'patch230-manifest.json').read_bytes()),'delta_files':len(files),'final_tests':logs[-1]['tests'],'final_seconds':logs[-1]['seconds']},indent=2))
