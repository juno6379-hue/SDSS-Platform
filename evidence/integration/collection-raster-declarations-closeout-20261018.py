"""Freeze144 new collection raster declarations evidence; no operating writes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,subprocess
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2];P='evidence/integration/'
def record(name):
    raw=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/144_collection_raster_declarations.md']:
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
closeout={'status': '144_NEW_COLLECTION_RASTER_DECLARATIONS', 'focused': {'tests': 7, 'passed': 7, 'skipped': 0, 'seconds': 3.086, 'log': 'evidence/integration/collection-raster-declarations-agent-20261018.log'}, 'related': {'tests': 156, 'passed': 155, 'skipped': 1, 'seconds': 69.832, 'log': 'evidence/integration/collection-raster-declarations-root-related-20261018.log'}, 'full_backend': {'tests': 1426, 'passed': 1425, 'skipped': 1, 'seconds': 296.344, 'log': 'evidence/integration/collection-raster-declarations-full-20261018.log'}, 'independent': {'schema_version': 1, 'scope': 'INDEPENDENT_NEW_COLLECT_WINDOWS_DECLARATIONS_TEMP_ONLY', 'git_baseline': 'bd03292ea12f642839c96b753b752061725ef8d2', 'tests': 7, 'passed': 7, 'skipped': 0, 'failures': 0, 'errors': 0, 'seconds': 4.489371699994081, 'source_sha256': 'a78d0293736780e70402b85714f38964c2ef09e1253cf7453e292ca9a2551c98', 'test_sha256': '469ff453b37a91a4f6d7cf890e5721b9c0aeec31df2a28b215c1017e9f8c821e', 'test_names': ['test_00_frozen_source_test_and_only_collect_windows_ast_changed', 'test_01_pc_six_bands_actual_descriptions_nodata_and_values', 'test_02_finite_nonzero_without_scl_and_original_crops_preserved', 'test_03_scl_codes_separate_from_finite_predicate', 'test_04_earth_search_logical_order_unknown_and_permutation_not_repaired', 'test_05_actual_new_outputs_explicit_setup_report_registration_and_consumption', 'test_06_baseline_comparison_raw_source_bytes_and_old_nan_limitation'], 'old_sources_unchanged': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True, 'scripts/collect_training_grid.py': True, 'scripts/collect_training_parallel.py': True, 'backend/app/data/budget.py': True}, 'separate_git_baseline_matches': {'backend/app/data/quality_report_preflight.py': True, 'tests/test_quality_report_preflight.py': True, 'backend/app/data/quality_report_storage.py': True, 'backend/app/data/quality_report_completion.py': True, 'backend/app/dataset_registry.py': True, 'backend/app/store.py': True, 'backend/app/ml/registered_quality_mask_files.py': True, 'backend/app/ml/registered_binary_mask_values.py': True, 'backend/app/main.py': True, 'frontend/src/AnnualInputDiagnostics.tsx': True, 'backend/app/data/quality_report_registration.py': True, 'tests/test_quality_report_registration.py': True, 'scripts/collect_training_grid.py': True, 'scripts/collect_training_parallel.py': True, 'backend/app/data/budget.py': True}, 'observations': [{'source_AST': 'all top-level nodes other than collect_windows unchanged against baseline', 'baseline': 'bd03292ea12f642839c96b753b752061725ef8d2'}, {'actual': 'collect_windows execute=True on new Temp GTiffs', 'network': 'search_stac/read_cog_window explicitly mocked', 'normal_mask_counts': {'valid': 16, 'invalid': 0, 'total': 16}, 'model_approval': False}, {'actual': 'PC and EarthSearch ordered names plus unknown/permuted inputs', 'unknown_asset': 'preserved verbatim', 'permuted_129_gate': 'BLOCKED; producer did not reorder'}, {'actual': 'new collector outputs -> explicit caller manifest/metadata/semantics ->140141142 ->133 readonly', 'separate_setup_registry_writes': 2, 'report_registration': 1, 'counts': {'valid_pixels': 9, 'invalid_pixels': 7, 'total_pixels': 16}, 'automatic_collector_registration': False, 'calibration_units_and_scientific_approval': False}, {'actual_baseline_comparison': 'same mocked arrays, separate Temp outputs; baseline module loaded from git bytes without product edits', 'raw_source_crop_bytes_identical': 6, 'baseline_nonzero_nan_inf_valid_pixels': 15, 'new_finite_nonzero_valid_pixels': 12, 'total_pixels': 16}], 'actual_scope': 'new temporary GTiff header and pixel outputs; separate caller metadata and temporary report storage/registration/readonly consumption', 'mock_scope': 'STAC search and COG window arrays are explicit service mocks; socket network guard; no real collection or source download', 'operating_collection': 0, 'operating_writes': 0, 'network_requests': 0, 'training': 0, 'inference': 0, 'api_ui_changed': False, 'frontend_build_browser_required': False, 'limitations': ['Band names preserve requested order and unknown asset names; no taxonomy/calibration/unit or physical source authenticity is established.', 'Explicit binary mask validity is finite/nonzero and existing SCL exclusions, not independent quality truth or scientific/model/execution approval.', 'Integration manifests/metadata and Registry source setup are explicit temporary caller steps, not automatic collector registration.', 'Only new collect_windows outputs change. Existing datasets/raw source crops/grid label masks and operating ledgers/reservations are not migrated.']}, 'integrity': {'recorded_at': '2026-10-18T07:10:00.299981+09:00', 'protected_files_checked': 141, 'protected_changes': [], 'snapshot_existing_source_checked': 326, 'supplemental_git_baseline_source': 'scripts/collect_samples.py', 'baseline_commit': 'bd03292ea12f642839c96b753b752061725ef8d2', 'initial_audit_scope_correction': 'Published snapshot omitted collector; initial 326-source unchanged count excluded it. Pinned Git blob supplements that scope; initial JSON is preserved.', 'existing_source_checked': 327, 'existing_source_changes': [{'path': 'scripts/collect_samples.py', 'before': {'sha256': '418a0237d80c77fe0f70ca52feef1144192e9ac8916696888a7ee9b5b34946e6', 'bytes': 46016}, 'after': {'sha256': 'a78d0293736780e70402b85714f38964c2ef09e1253cf7453e292ca9a2551c98', 'bytes': 46415}}], 'unexpected_existing_source_changes': [], 'expected_changed_existing_sources': [{'path': 'scripts/collect_samples.py', 'before': {'sha256': '418a0237d80c77fe0f70ca52feef1144192e9ac8916696888a7ee9b5b34946e6', 'bytes': 46016}, 'after': {'sha256': 'a78d0293736780e70402b85714f38964c2ef09e1253cf7453e292ca9a2551c98', 'bytes': 46415}}], 'unchanged_existing_source_files': 326, 'previous_evidence_checked': 1381, 'previous_evidence_changes': [], 'catalog_rows': 14, 'catalog_canonical_sha256': '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b', 'reserved_bytes_preserved': 136314880, 'existing_execution_workflow_model_and_other_sources_unchanged': True, 'operating_collection_training_registry_deployment_workflow_dispatch': 0}, 'understanding_updated': True, 'web_ui_api_changed': False, 'backend_full_rerun_this_unit': True, 'frontend_build_browser_rerun_this_unit': False, 'operating_collection_training_registry_approval_deployment_workflow_dispatch': 0, 'existing_outputs_backfilled': False, 'raw_existing_source_files_rewritten': False, 'future_derived_labels_can_change_at_nonfinite_pixels': True, 'scientific_accuracy_validated': False, 'execution_authorized': False, 'workflow_supported': False, 'next_internal_candidate': '145_GRID_PATCH_BAND_DESCRIPTION_AND_IMAGE_QUALITY_VS_LABEL_SUPPORT_SEPARATION_REVIEW'}
closeout['recorded_at']=audit['checked_at'];closeout['documentation_validation']=audit
closeout['integrity']=json.loads((ROOT/P/'collection-raster-declarations-live-integrity-final-20261018.json').read_text('utf-8'))
assert not closeout['integrity']['protected_changes'] and not closeout['integrity']['unexpected_existing_source_changes'] and not closeout['integrity']['previous_evidence_changes']
closeout['source_records']={n:record(n) for n in ['scripts/collect_samples.py','tests/test_collection_raster_declarations.py']}
assert closeout['source_records']['scripts/collect_samples.py']['sha256']==closeout['independent']['source_sha256']
assert closeout['source_records']['tests/test_collection_raster_declarations.py']['sha256']==closeout['independent']['test_sha256']
processes=json.loads((ROOT/P/'collection-raster-declarations-final-processes-20261018.json').read_text('utf-8-sig'))
assert processes['automation_status']=='ACTIVE' and processes['collector_training_processes_observed']==0
closeout['live_processes']=processes
closeout['operating_inventory']=json.loads((ROOT/P/'collection-raster-declarations-operating-inventory-20261018.json').read_text('utf-8'))
closeout['previous_full_backend']={'unit':137,'passed':1358,'skipped':1,'seconds':484.770}
closeout['previous_frontend']={'unit':137,'passed':271,'build_modules':112,'build_seconds':13.48}

closeout['approved_source_scope']=json.loads((ROOT/P/'collection-raster-declarations-source-scope-20261018.json').read_text('utf-8'))
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
names=set(snapshot['files'])|(publish-tracked)|changed
target=ROOT/P/'collection-raster-declarations-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='bd03292ea12f642839c96b753b752061725ef8d2'
snapshot['source_commit_reason']='Published143 baseline plus144 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=True
snapshot['reported_status']['latest_collection_raster_declarations']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['reported_status']['latest_full_backend']={'unit':144,**closeout['full_backend']}
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
