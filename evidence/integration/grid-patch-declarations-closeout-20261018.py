"""Freeze145 grid patch declarations evidence; no operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/145_grid_patch_declarations.md']:
    text=path.read_text('utf-8')
    if 'understanding' in path.parts and path.name!='GATE_TEMPLATE.md':
        for field in ('updated_at','source_commit','evidence_paths','confidence','status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|',text,re.M):errors.append(path.name+': missing '+field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|',line):
                for name in re.findall(r'`([^`]+)`',line):
                    references+=1
                    if not (ROOT/name).exists():errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)',text):
        name=unquote(value.strip('<>').split('#',1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:',name):continue
        links+=1
        if not (path.parent/name).exists():errors.append(path.name+': missing link '+name)
faq=len(re.findall(r'^## \d+\.',(ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'),re.M))
assert faq==10 and not errors,errors
assert (ROOT/'docs/understanding/GATE_TEMPLATE.md').read_bytes()==(ROOT/'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md').read_bytes()
audit={'checked_at':datetime.now().astimezone().isoformat(),'understanding_markdown':len(documents),'implementation_markdown':1,'local_links':links,'metadata_evidence_references':references,'numbered_faq':faq,'errors':errors,'reference_templates_byte_identical':True}
closeout={'status': '145_GRID_PATCH_DECLARATIONS', 'focused': {'tests': 6, 'passed': 6, 'skipped': 0, 'seconds': 2.778, 'log': 'evidence/integration/grid-patch-declarations-agent-20261018.log'}, 'related': {'tests': 171, 'passed': 170, 'skipped': 1, 'seconds': 79.284, 'log': 'evidence/integration/grid-patch-declarations-root-related-20261018.log'}, 'full_backend': {'tests': 1432, 'passed': 1431, 'skipped': 1, 'seconds': 332.72, 'log': 'evidence/integration/grid-patch-declarations-full-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_GRID_PATCH_DECLARATIONS_TEMP_ONLY', 'git_baseline': 'a3f4a94a69ad0f5c54a9af76bf6af82053e1a419', 'tests': 7, 'passed': 7, 'skipped': 0, 'failures': 0, 'errors': 0, 'seconds': 4.2726165000058245, 'source_sha256': 'd312660f1a25fb6a9477f101e09aacd14f543636614726fb13092f42bceda3d6', 'test_sha256': 'f183ba9e6469e5fff225d2ebd163fea2c54bcadf3f6bc604f53046aa2af38805', 'test_names': ['test_00_source_hash_and_ast_scope', 'test_01_actual_descriptions_none_unknown_and_permutation_unchanged', 'test_02_baseline_arrays_profiles_label_quality_bytes_and_rows_equal', 'test_03_no_scene_semantics_still_training_support_and_detached', 'test_04_actual_pixel_intersection_label_support_and_class_counts', 'test_05_actual_aoi_intersection_matches_baseline_no_default_reclassification', 'test_06_actual_low_level_consumer_header_and_intrinsic_nodata_boundary'], 'old_sources_unchanged': {'scripts/collect_samples.py': True, 'scripts/collect_training_parallel.py': True, 'backend/app/data/budget.py': True, 'backend/app/main.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/ml/registry_raster_grid_normalization.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'separate_git_baseline_matches': {'scripts/collect_samples.py': True, 'scripts/collect_training_parallel.py': True, 'backend/app/data/budget.py': True, 'backend/app/main.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/ml/registry_raster_grid_normalization.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True}, 'observations': [{'actual': 'six ordered/None/mixed unknown/permuted image descriptions, two patches each', 'label_and_quality_descriptions': [None], 'source_inputs_and_report_unchanged': True}, {'actual_baseline_comparison': 'isolated Git module with same Temp inputs', 'patches': 2, 'image_arrays_profiles_equal': True, 'label_quality_raw_bytes_equal': True, 'rows_split_classcounts_equal_except_explicit_declarations_paths_and_hashes': True}, {'actual_low_level_consumers': {'129_header': 'MATCHED ordered six-band header only', '129_permutation': 'RASTER_BAND_SIGNATURE_INVALID', '133_binary_counts': 'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'}, 'full_registry_consumer_executed': False, 'Store_calls': 0, 'training_support_is_not_pure_quality_mask': True}], 'actual_scope': 'Temp source GTiffs/scene-report/explicit boundary fixture; native patch writer and baseline pixel/profile/label-quality bytes; low-level129/133 readers only', 'mock_scope': 'Only module ROOT redirected to explicit Temp provenance GeoJSON and socket network denial guard; no mocked raster arrays or full Registry success claim', 'operating_writes': 0, 'operating_collection': 0, 'network_requests': 0, 'Store_calls': 0, 'training': 0, 'inference': 0, 'api_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Patch quality is training support combining label/AOI/source quality and image finite/nonzero, not a pure image validity or GMAIS approval.', 'materialize_patches already uses mkdir(exist_ok=True) and open(w); this change does not enforce new-file-only or no-overwrite semantics.', 'No existing datasets/headers/scene reports are migrated and no scientific/model/execution approval is granted.', 'Low-level129 header/133 intrinsic-validity checks do not execute full Registry consumers or verify complete source semantics.']}, 'integrity': {'recorded_at': '2026-10-18T07:23:48.611615+09:00', 'baseline_scope': 'ALL_TRACKED_SOURCE_FILES_PLUS_PUBLISHED_SNAPSHOT', 'baseline_commit': 'a3f4a94a69ad0f5c54a9af76bf6af82053e1a419', 'tracked_source_baseline_count': 431, 'protected_files_checked': 141, 'protected_changes': [], 'existing_source_checked': 431, 'existing_source_changes': [{'path': 'scripts/collect_training_grid.py', 'before': {'sha256': '3cdcc6c0baa785b9df8a1396b5898d6134851b6b4f9ad864e48daec8a77ba994', 'bytes': 24789}, 'after': {'sha256': 'd312660f1a25fb6a9477f101e09aacd14f543636614726fb13092f42bceda3d6', 'bytes': 25287}}], 'unexpected_existing_source_changes': [], 'expected_changed_existing_sources': [{'path': 'scripts/collect_training_grid.py', 'before': {'sha256': '3cdcc6c0baa785b9df8a1396b5898d6134851b6b4f9ad864e48daec8a77ba994', 'bytes': 24789}, 'after': {'sha256': 'd312660f1a25fb6a9477f101e09aacd14f543636614726fb13092f42bceda3d6', 'bytes': 25287}}], 'unchanged_existing_source_files': 430, 'previous_evidence_checked': 1399, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'web_ui_api_changed': False, 'backend_full_rerun_this_unit': True, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'source_report_mutated': False, 'old_outputs_backfilled': False, 'overwrite_guard_added': False, 'mask_pixels_and_nodata_policy_changed': False, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'next_internal_candidate': '146_EXPLICIT_SOURCE_RASTER_DATASET_VERSION_REGISTRATION_CLI_REVIEW', 'separate_followup_candidate': 'GEOLLM_EXPLICIT_VERIFIED_LOCAL_LCLUC_WORKFLOW_REPORT_EVIDENCE_VIEW'}
closeout['recorded_at']=audit['checked_at'];closeout['documentation_validation']=audit
closeout['integrity']=json.loads((ROOT/P/'grid-patch-declarations-live-integrity-final-20261018.json').read_text('utf-8'))
assert not closeout['integrity']['protected_changes'] and not closeout['integrity']['unexpected_existing_source_changes'] and not closeout['integrity']['previous_evidence_changes']
closeout['source_records']={n:record(n) for n in ['scripts/collect_training_grid.py','tests/test_grid_patch_declarations.py']}
assert closeout['source_records']['scripts/collect_training_grid.py']['sha256']==closeout['independent']['source_sha256']
assert closeout['source_records']['tests/test_grid_patch_declarations.py']['sha256']==closeout['independent']['test_sha256']
processes=json.loads((ROOT/P/'grid-patch-declarations-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'grid-patch-declarations-operating-inventory-20261018.json').read_text('utf-8'))
closeout['previous_full_backend']={'unit':144,'passed':1425,'skipped':1,'seconds':296.344}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}

closeout['approved_source_scope']=json.loads((ROOT/P/'grid-patch-declarations-source-scope-20261018.json').read_text('utf-8'))
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
pre=json.loads((ROOT/P/'grid-patch-declarations-preflight-20261018.json').read_text('utf-8'))
names=set(snapshot['files'])|set(pre['tracked_source_baseline'])|(publish-tracked)|changed
target=ROOT/P/'grid-patch-declarations-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='a3f4a94a69ad0f5c54a9af76bf6af82053e1a419'
snapshot['source_commit_reason']='Published144 baseline plus145 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=True
snapshot['reported_status']['latest_grid_patch_declarations']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['reported_status']['latest_full_backend']={'unit':145,**closeout['full_backend']}
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
