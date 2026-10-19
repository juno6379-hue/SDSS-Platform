"""279 신규 패치0의 읽기 전용 좁은 감사. Root GO 전 실행 금지."""
from pathlib import Path
import argparse
import json
import sys
import subprocess
from datetime import datetime, timezone
from contextlib import redirect_stdout, redirect_stderr

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'backend'), str(ROOT)]
from audit_priority_increment165 import read_json, snapshot, sha, canonical, effective_config, local


def run(out, go_path):
    ev = ROOT / 'evidence/integration'
    data = ROOT / 'data'
    read = lambda p, cap=16 << 20: read_json(p, cap)[1]
    go = read(go_path, 1 << 20)
    assert go['status'] == 'GO_NARROW_ZERO_PATCH_AUDIT'
    assert go['runner_sha256'] == sha(snapshot(Path(__file__), 1 << 20))
    launch_path = ev / 'deficit279-launch-root-20261018.json'
    launch_raw, launch = read_json(launch_path, 1 << 20)
    terminal = read(ev / 'deficit279-terminal-root-20261018.json', 1 << 20)
    request = read(ev / 'deficit279-request-root-20261018.json', 1 << 20)
    assert sha(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode()) == launch['request_sha256']
    assert terminal['exit_code'] == 0 and terminal['lock_present'] is False
    job, = launch['selected_jobs']
    key = job['key']
    assert launch['maximum_new_physical_patches'] == 16
    mp = data / 'first-group-training-esri-v1/annual-window-report.json'
    lp = data / 'first-group-training-budget/global-ledger.json'
    assert not (lp.parent / 'global-ledger.execution.lock').exists()
    os_query = "$x=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and ($_.CommandLine -match 'collect_deficit_guarded.py|deficit279-supervisor-root') }; @($x | Select-Object ProcessId,ParentProcessId,Name) | ConvertTo-Json -Compress"
    proc = subprocess.run(['powershell', '-NoProfile', '-Command', os_query], capture_output=True, text=True, timeout=20, check=True)
    observed = json.loads(proc.stdout.strip()) if proc.stdout.strip() else []
    assert observed == [], 'COLLECTOR_PROCESS_PRESENT'
    mr, manifest = read_json(mp, 128 << 20)
    lr, ledger = read_json(lp, 16 << 20)
    assert sha(mr) == go['source_sha256'] and sha(lr) == go['ledger_sha256']
    pr, prior = read_json(local(ROOT, request['current_manifest_ref']['path']), 128 << 20)
    assert sha(pr) == request['current_manifest_ref']['sha256'] == launch['manifest_before_sha256']
    assert len(prior['scenes']) == launch['source_rows_before'] == 1731
    assert manifest['scenes'] == prior['scenes']
    assert manifest.get('historical_noneligible_patches', []) == prior.get('historical_noneligible_patches', [])
    assert len(launch['pending_before']) == 2
    assert all(ledger['batches'].get(k) == v for k, v in launch['pending_before'].items())
    batch = ledger['batches'][key]
    assert batch['status'] == 'settled'
    source = mp.parent / 'sources' / key
    documents = {}
    pins = {}
    for name in ('config.json', 'window-state.json', 'worker-result.json', 'annual-window-report.json', 'selection-context.json'):
        raw, obj = read_json(source / name, 16 << 20)
        documents[name] = obj
        pins[str(source / name)] = sha(raw)
    config, state, worker, report = [documents[x] for x in ('config.json', 'window-state.json', 'worker-result.json', 'annual-window-report.json')]
    assert canonical(config) == job['config_sha256'] == batch['config_sha256']
    assert canonical(effective_config(config)) == state['config_sha256']
    assert job['province'] == 'gorontalo' and job['split'] == 'train' and job['year'] == 2025
    assert worker['key'] == key
    assert local(ROOT, worker['report_path']) == source / 'annual-window-report.json' == local(ROOT, batch['report_path'])
    charge = worker['charged_bytes']
    assert all(type(x) is int and x >= 0 for x in (charge, batch['charged_bytes'], state['http_body_bytes'], worker['metadata_budget']['charged_bytes'], worker['cog_charged_bytes']))
    assert charge == batch['charged_bytes'] == state['http_body_bytes'] + worker['metadata_budget']['charged_bytes'] == worker['cog_charged_bytes'] + worker['metadata_budget']['charged_bytes']
    lines = [json.loads(x) for x in (ev / 'deficit279-live-root-20261018-stdout.log').read_text('utf-8-sig').splitlines() if x.strip()]
    final = lines[-1]
    assert final['status'] == 'BOUNDED_DEFICIT_STAGE_FINISHED' and final['request_sha256'] == launch['request_sha256']
    assert final['execution']['submitted_batches'] == final['execution']['finalized_batches'] == 1
    assert all(final['execution_progress'][n] == [key] for n in ('finalization_attempted_batches', 'settled_batches', 'published_batches'))
    item, = final['batches']
    assert item['patches'] == item['eligible'] == 0 and item['charged_bytes'] == charge
    assert worker['live_b02_checked'] is item['live_b02_checked'] is False
    summaries, candidates, scenes = [], [], []
    scl_checks = []
    for scene in report.get('scenes', []):
        scenes.append({k: scene.get(k) for k in ('scene_id', 'status', 'quality_status', 'error', 'b02_alignment_diagnostic')})
        if scene.get('label_first_preview') is not None:
            preview = scene['label_first_preview']
            scenes[-1]['label_first_preview'] = {k: preview.get(k) for k in ('year', 'class_counts', 'selection_context', 'note')}
            counts = preview['class_counts']
            total = sum(counts.values())
            context = preview['selection_context']
            priority = sum(counts.get(str(c), 0) for c in context.get('priority_source_classes', []))
            scenes[-1]['stored_preview_total_pixels'] = total
            scenes[-1]['stored_preview_dominant_fraction'] = max(counts.values(), default=0) / max(total, 1)
            scenes[-1]['stored_preview_priority_fraction'] = priority / max(total, 1)
            scenes[-1]['preview_array_independently_recounted'] = False
        summary = scene.get('candidate_metadata_filter')
        if summary is not None:
            assert summary['policy'] == config['candidate_metadata_policy'] == request['candidate_metadata_policy'] == 'DEFICIT_AOI_BBOX_CONTAINS_V1'
            assert summary['request_sha256'] == launch['request_sha256']
            assert summary['source_sha256'] == launch['manifest_before_sha256']
            n = summary['input_count']
            assert type(n) is int and 0 <= n <= 20 and len(summary['items']) == n
            assert sorted(x['input_index'] for x in summary['items']) == list(range(n))
            assert sorted(x['cloud_rank'] for x in summary['items']) == list(range(n))
            assert summary['retained_count'] + summary['excluded_count'] == n
            assert summary['selected_pool_count'] == min(config['candidate_limit'], summary['retained_count']) <= 5
            assert not any(x in json.dumps(summary) for x in ('http:', 'https:', '?sig='))
            summaries.append(summary)
        for candidate in scene.get('candidate_selection', []):
            value = {k: candidate.get(k) for k in ('scene_id', 'status', 'estimated_valid_fraction', 'minimum_fraction', 'error', 'raw_scl_sha256', 'b02_alignment_diagnostic')}
            if candidate.get('raw_scl_path'):
                p = local(ROOT, candidate['raw_scl_path'])
                assert p.is_relative_to(source)
                raw = snapshot(p, 4 << 20)
                assert sha(raw) == candidate['raw_scl_sha256']
                pins[str(p)] = sha(raw)
                scl_checks.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(raw), 'bytes': len(raw)})
            candidates.append(value)
    patch_files = list((mp.parent / 'patches' / key).rglob('*.tif'))
    assert not patch_files
    for name, pin in pins.items():
        assert sha(snapshot(Path(name), 16 << 20)) == pin
    assert snapshot(mp, 128 << 20) == mr and snapshot(lp, 16 << 20) == lr
    assert snapshot(launch_path, 1 << 20) == launch_raw
    assert not (lp.parent / 'global-ledger.execution.lock').exists()
    out.update(status='COMPLETED_ZERO_PATCH_NARROW_AUDIT', recorded_at=datetime.now(timezone.utc).isoformat(),
        terminal_exit_code=terminal['exit_code'], terminal_seconds=terminal['seconds'],
        original_launch_sha256=sha(launch_raw), request_sha256=launch['request_sha256'],
        before_source_sha256=sha(pr), source_sha256=sha(mr), source_bytes=len(mr), ledger_sha256=sha(lr),
        before_ledger_sha256=launch['ledger_before_sha256'], old_rows_exact=True, old_history_exact=True,
        old_pending_exact=True, old_pending_reserved_bytes=sum(v['reserved_bytes'] for v in launch['pending_before'].values()),
        changed_manifest_keys=[k for k in set(prior) | set(manifest) if prior.get(k) != manifest.get(k)],
        registered_total=len(manifest['scenes']), eligible_total=manifest.get('quality_eligible_window_count'),
        new_patch_files=0, new_eligible_patches=0, new_bare_contribution_patches=0,
        stored_config_sha256=canonical(config), effective_config_sha256=state['config_sha256'],
        worker_error=worker.get('error'), worker_b02_alignment_diagnostic=worker.get('b02_alignment_diagnostic'),
        scene_observations=scenes, candidate_observations=candidates, metadata_filter_summaries=summaries,
        independent_raw_scl_sha_checks=scl_checks, bounded_file_pins=pins, execution_progress=final['execution_progress'],
        physical_before=final['physical_inventory_before'], physical_after_inferred=final['physical_inventory_before']['physical_patch_count'],
        cog_charged_bytes=worker['cog_charged_bytes'], metadata_charged_bytes=worker['metadata_budget']['charged_bytes'],
        total_settled_bytes=charge, new_charged_bytes=ledger['new_charged_bytes'], remaining_budget=ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
        source_ledger_two_reads_stable=True, collector_os_exit_observed=True, lock_absent=True,
        limitations=['새 SCL은 저장바이트 SHA만 검사했으며 픽셀 배열 재측정은 하지 않았다.', '후보 수·탈락 사유는 저장된 보고서에서 집계했다. 원격 원문 검색 응답을 재요청하지 않았다.', '실물 총량은 수집기 사전검사와 신규 패치 없음에 근거하며 기존 전체 파일을 재검사하지 않았다.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-go', type=Path, required=True)
    args = parser.parse_args()
    prefix = ROOT / 'evidence/integration/deficit279-native-root-20261018'
    out = {'status': 'INCOMPLETE', 'native_validation_complete': False, 'native_raster_reads': 0,
           'reviewer_http_calls': 0, 'reviewer_collection_starts': 0, 'operating_writes': 0,
           'learning_ready': False, 'scientific_accuracy_validated': False}
    with Path(str(prefix)+'.json').open('x', encoding='utf-8') as output, Path(str(prefix)+'.log').open('x', encoding='utf-8') as log, Path(str(prefix)+'-stderr.log').open('x', encoding='utf-8') as error:
        try:
            with redirect_stdout(log), redirect_stderr(error):
                run(out, args.root_go)
        except Exception as exc:
            import traceback
            out.update(status='INCOMPLETE_PRESERVED_NO_RETRY', issue_type=type(exc).__name__)
            traceback.print_exc(file=error)
        finally:
            json.dump(out, output, ensure_ascii=False, indent=2)
    print(json.dumps({'status': out['status']}, ensure_ascii=True))
    return 0 if out['status'] == 'COMPLETED_ZERO_PATCH_NARROW_AUDIT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
