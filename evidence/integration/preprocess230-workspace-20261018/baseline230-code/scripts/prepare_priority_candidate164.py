"""Prepare one new SHA-pinned, leak-filtered candidate; never train or publish it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / '.runtime'), str(ROOT / 'backend')]
from backend.app.ml.split_json_io import _local,BoundedJSONIO
from backend.app.ml.manifest_resource_profile import entry as profile_entry,active,cap as profile_cap,charge as profile_charge,read_json as profile_read_json,NAME,require_io_room,MARKER
from backend.app.ml.candidate_materialization import POLICY
from backend.app.data.recovery_terminal import _confined
from backend.app.ml.readiness import assess
from backend.app.ml.split_planning import plan_split_repair, write_plan
from backend.app.ml.candidate_materialization import materialize_split_candidate
from backend.app.ml.candidate_staging import stage_split_candidate
from backend.app.ml.candidate_readiness_qa import assess_staged_candidate


def digest(path):
    h = hashlib.sha256()
    if active() is not None and path.suffix=='.json':
        maximum=128*1024**2
        if path.stat().st_size>maximum:raise ValueError('MANIFEST_JSON_FILE_LIMIT')
        require_io_room(maximum+1);count=0
        with path.open('rb') as stream:
            while True:
                chunk=stream.read(min(1024*1024,maximum+1-count))
                if not chunk:break
                profile_charge(len(chunk));count+=len(chunk)
                if count>maximum:raise ValueError('MANIFEST_JSON_FILE_LIMIT')
                h.update(chunk)
        return h.hexdigest()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    if active() is not None:
        bounded=BoundedJSONIO({'input_caps':dict(POLICY['input_caps']),'output_caps':{'plan':16*1024**2 if path.name=='source-readiness.json' else 4*1024**2,'candidate':65536},'max_depth':32})
        profile_charge(bounded.measure(value,'plan')+len(os.linesep.encode()),'write')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def copy_pinned(source, output, pin, cap=64 * 1024**2):
    """Bounded exclusive copy. A failed partial copy is preserved, never reused."""
    cap=profile_cap('source',cap)
    if not source.is_file() or source.is_symlink() or source.stat().st_size > cap:
        raise ValueError('Source must be a bounded regular local file')
    before = source.stat()
    require_io_room(2*before.st_size)
    if digest(source) != pin:
        raise ValueError('Source pin differs before copy')
    require_io_room(2*before.st_size)
    h = hashlib.sha256(); count = 0
    with source.open('rb') as src, output.open('xb') as dst:
        opened = os.fstat(src.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise ValueError('Source changed before descriptor copy')
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            count += len(chunk)
            if count > cap or count > before.st_size:
                raise ValueError('Source grew during copy')
            profile_charge(len(chunk));profile_charge(len(chunk),'write');dst.write(chunk); h.update(chunk)
    after = source.stat()
    if count != before.st_size or h.hexdigest() != pin or digest(source) != pin or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
        raise ValueError('Source changed during copy')
    if digest(output) != pin:
        raise ValueError('Snapshot pin differs')
    return count


@profile_entry
def prepare(data_root, source, source_pin, policy, policy_pin, run_id, *, evidence_root=None):
    for pin in (source_pin, policy_pin):
        if type(pin) is not str or re.fullmatch('[0-9a-f]{64}', pin) is None:
            raise ValueError('Explicit lowercase SHA256 required')
    if type(run_id) is not str or re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', run_id) is None:
        raise ValueError('Safe explicit run ID required')
    for p in (data_root, source, policy):
        if not Path(p).is_absolute():
            raise ValueError('Explicit absolute local paths required')
        _local(p)
    data = Path(data_root).resolve()
    if not data.is_dir():
        raise ValueError('Existing DATA root required')
    source = Path(source); policy = Path(policy)
    _confined(data, source); _confined(data, policy)
    if source.resolve() == policy.resolve() or not policy.is_file() or policy.is_symlink() or policy.stat().st_size > 1024**2:
        raise ValueError('Distinct bounded policy required')
    if digest(source) != source_pin or digest(policy) != policy_pin:
        raise ValueError('Caller pin differs')
    evidence = Path(evidence_root or ROOT / 'evidence/integration').resolve()
    _local(evidence)
    if not evidence.is_dir() or evidence.is_relative_to(data) or data.is_relative_to(evidence):
        raise ValueError('Existing disjoint evidence root required')
    work = data / ('priority164-' + run_id)
    out = evidence / ('priority164-' + run_id)
    if any(p.exists() or p.is_symlink() for p in (work, out)):
        raise ValueError('New run paths required; existing/partial runs preserved')
    work.mkdir(exist_ok=False); out.mkdir(exist_ok=False)
    snapshot = work / 'source.json'
    size = copy_pinned(source, snapshot, source_pin)
    policy_doc = profile_read_json(policy,'source',maximum=1024**2) if active() is not None else json.loads(policy.read_text(encoding='utf-8'))
    document = profile_read_json(snapshot,'source') if active() is not None else json.loads(snapshot.read_text(encoding='utf-8'))
    rows = document['scenes']
    if not rows or not all(Path(r[k]).is_absolute() for r in rows for k in ('image_path', 'label_path', 'quality_mask_path')):
        raise ValueError('Snapshot requires nonempty rows with absolute raster paths')
    stamp = datetime.now(timezone.utc).isoformat()
    write_new(out / 'preflight.json', {'at': stamp, 'source_original': str(source), 'source_snapshot': str(snapshot), 'source_sha256': source_pin, 'source_bytes': size, 'source_row_count': len(rows), 'policy_sha256': policy_pin, 'scope': 'PINNED_COHORT_EXCLUDES_LATER_COLLECTION', 'training_executed': False, 'network_requests': 0})
    print(json.dumps({'stage': 'SNAPSHOT_PINNED', 'at': stamp, 'rows': len(rows), 'source_sha256': source_pin}), flush=True)
    for key, value in {'PROJ_NETWORK': 'OFF', 'GDAL_PAM_ENABLED': 'NO', 'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'GDAL_VRT_ENABLE_PYTHON': 'NO'}.items():
        os.environ[key] = value
    start = time.monotonic()
    raw_report = assess([snapshot], data, policy_doc, connectivity_diagnostics=True)
    raw_seconds = round(time.monotonic() - start, 3)
    old_readiness = work / 'source-readiness.json'; write_new(old_readiness, raw_report)
    print(json.dumps({'stage': 'SOURCE_QA_COMPLETE', 'seconds': raw_seconds, 'eligible': raw_report['patch_counts_by_split']}), flush=True)
    if digest(snapshot) != source_pin or digest(policy) != policy_pin:
        raise ValueError('Pinned input changed after source QA')
    plan = plan_split_repair(snapshot, source_pin, province_splits=policy_doc['province_splits'], readiness_path=old_readiness, readiness_sha256=digest(old_readiness), data_root=data,**({'io_policy':BoundedJSONIO(POLICY)} if active() is not None else {}))
    saved = out / 'split-plan.json'; write_plan(plan, saved,**({'io_policy':BoundedJSONIO(POLICY)} if active() is not None else {}))
    paths = {'source': snapshot, 'readiness': old_readiness, 'saved_plan': saved}
    pins = {k: digest(p) for k, p in paths.items()}
    package = out / 'candidate-package'
    receipt = materialize_split_candidate(data, paths, pins, package, evidence_root=evidence)
    stage_dir = work / 'stage'
    stage_split_candidate(data, package, digest(package / 'receipt.json'), pins, stage_dir, evidence_root=evidence)
    print(json.dumps({'stage': 'CANDIDATE_STAGED', 'excluded_rows': len(plan['excluded_row_indexes']), 'eligible': plan['projected_after']['eligible_patches_by_split']}), flush=True)
    qa_paths = {'candidate': stage_dir / 'candidate.json', 'staging_receipt': stage_dir / 'staging-receipt.json', 'policy': policy, 'old_readiness': old_readiness}
    qa_pins = {k: digest(p) for k, p in qa_paths.items()}
    qa_dir = work / 'qa'; start = time.monotonic()
    qa_receipt = assess_staged_candidate(data, qa_paths, qa_pins, qa_dir)
    qa_seconds = round(time.monotonic() - start, 3)
    report = profile_read_json(qa_dir/'readiness.json','readiness') if active() is not None else json.loads((qa_dir / 'readiness.json').read_text(encoding='utf-8'))
    if digest(snapshot) != source_pin or digest(policy) != policy_pin or any(digest(p) != qa_pins[k] for k, p in qa_paths.items()):
        raise ValueError('Pinned input changed after candidate QA')
    # Recheck actual files after the native gate, without invoking training.
    mismatches = [r['path'] for r in report['verified_files'] if digest(data / r['path']) != r['sha256']]
    if mismatches:
        raise ValueError('Actual QA file changed during final verification')
    outputs = [snapshot, old_readiness, saved, package / 'plan.json', package / 'candidate.json', package / 'receipt.json', *qa_paths.values(), qa_dir / 'readiness.json', qa_dir / 'qa-receipt.json']
    summary = {'status': 'PINNED_CANDIDATE_QA_COMPLETED', 'at': datetime.now(timezone.utc).isoformat(), 'source_snapshot_at': stamp, 'scope': 'PINNED_COHORT_EXCLUDES_LATER_COLLECTION', 'source_sha256': source_pin, 'source_row_count': len(rows), 'source_eligible': raw_report['patch_counts_by_split'], 'source_blockers': raw_report['blockers'], 'candidate_row_count': receipt['candidate_row_count'], 'candidate_eligible': report['patch_counts_by_split'], 'excluded_source_rows': len(plan['excluded_row_indexes']), 'remaining_source_identity_conflicts': plan['remaining_source_identity_conflicts'], 'candidate_blockers': report['blockers'], 'bare_pixels': {s: v[7] for s, v in report['class_counts_by_split'].items()}, 'bare_contributing_patches': {s: v[7] for s, v in report['class_patch_counts_by_split'].items()}, 'observed_gate_ready_for_training': report['ready_for_training'], 'ready_for_training': False, 'scientific_accuracy_validated': False, 'training_executed': False, 'network_requests': 0, 'registry_called': False, 'source_qa_seconds': raw_seconds, 'candidate_qa_seconds': qa_seconds, 'verified_file_records': len(report['verified_files']), 'file_sha_mismatches': 0, 'connectivity_capture_status': qa_receipt['connectivity_capture_status'], 'outputs': {str(p): {'sha256': digest(p), 'bytes': p.stat().st_size} for p in outputs}}
    if active() is not None:
        summary['manifest_profile']=dict(MARKER)
        summary['manifest_resource_usage_before_summary_write']={'json_io_bytes':active().bytes,'read_bytes':active().reads,'write_bytes':active().writes,'maximum_bytes':active().maximum}
    write_new(out / 'summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('data-root', 'source', 'policy'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--policy-sha256', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--manifest-profile',choices=[NAME],default=None)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.data_root, args.source, args.source_sha256, args.policy, args.policy_sha256, args.run_id,manifest_profile=args.manifest_profile)
        print(json.dumps({'stage': result['status'], 'candidate_eligible': result['candidate_eligible'], 'ready_for_training': False}), flush=True)
        return 0
    except (ValueError, OSError, TypeError, KeyError, IndexError, AssertionError):
        print(json.dumps({'status': 'PREPROCESSING_INCOMPLETE', 'partial_outputs_preserved': True, 'automatic_retry_allowed': False, 'training_executed': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
