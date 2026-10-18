$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$taskLedger = Join-Path $taskRoot 'data/first-group-training-budget/global-ledger.json'
$taskLock = Join-Path $taskRoot 'data/first-group-training-budget/global-ledger.execution.lock'
$taskBudgetLock = Join-Path $taskRoot 'data/first-group-training-budget/global-ledger.lock'
$taskBackup = Join-Path $taskRoot 'data/collection-continuation-backup-20261018'
$taskEvidence = Join-Path $taskRoot 'evidence/integration/collection-resume-handover-20261018.json'
$taskNext = Get-Content -LiteralPath (Join-Path $taskRoot 'evidence/integration/collection-resume-audit-20261018-next-jobs.json') -Raw | ConvertFrom-Json
$taskBaseline = Get-Content -LiteralPath (Join-Path $taskRoot 'evidence/integration/collection-resume-root-baseline-20261018.json') -Raw | ConvertFrom-Json
if (Test-Path -LiteralPath $taskBackup) { throw 'Unique backup directory already exists; do not repeat this launch.' }
if (Test-Path -LiteralPath $taskEvidence) { throw 'Handover already recorded; do not repeat this launch.' }
if (Test-Path -LiteralPath $taskBudgetLock) { throw 'Budget transaction lock is present.' }
$taskCollectors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w|[0-9.]*)?\.exe$' -and $_.CommandLine -match 'collect_training_parallel\.py|collect_training_grid\.py|collect_samples\.py|monitor_collection_progress\.py'
} | Select-Object ProcessId, CreationDate, Name, CommandLine)
if ($taskCollectors.Count -ne 0) { throw 'A collector or monitor exists; no lock handover permitted.' }
$taskExpected = $taskBaseline.files.PSObject.Properties[$taskLedger].Value
if ((Get-FileHash -LiteralPath $taskLedger -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpected.sha256) { throw 'Ledger changed after baseline.' }
$taskExpectedLock = $taskBaseline.files.PSObject.Properties[$taskLock].Value
if ((Get-FileHash -LiteralPath $taskLock -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpectedLock.sha256) { throw 'Execution lock changed after baseline.' }
if ((Get-Item -LiteralPath $taskLock).Length -ne 0) { throw 'Only the audited empty legacy lock can be handed over.' }
foreach ($taskJob in $taskNext.next_jobs) {
    if (Test-Path -LiteralPath (Join-Path $taskRoot ('data/first-group-training-esri-v1/sources/' + $taskJob.key))) {
        throw 'A next-job source directory already exists.'
    }
}
# All move targets are explicit, non-recursive, and inside this workspace.
$taskResolvedRoot = $taskRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
foreach ($taskPath in @($taskLock, $taskBackup, $taskEvidence)) {
    if (-not [System.IO.Path]::GetFullPath($taskPath).StartsWith($taskResolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes workspace.' }
}
New-Item -ItemType Directory -Path $taskBackup | Out-Null
$taskNames = @('global-ledger.json', 'annual-window-report.json', 'run-result.json', 'parallel-v2-plan.json')
$taskSources = @($taskLedger)
$taskSources += @('annual-window-report.json', 'run-result.json', 'parallel-v2-plan.json') | ForEach-Object { Join-Path $taskRoot ('data/first-group-training-esri-v1/' + $_) }
$taskBackups = @()
for ($taskIndex = 0; $taskIndex -lt $taskSources.Count; $taskIndex++) {
    $taskDestination = Join-Path $taskBackup $taskNames[$taskIndex]
    $taskSourceExpected = $taskBaseline.files.PSObject.Properties[$taskSources[$taskIndex]].Value
    if ((Get-FileHash -LiteralPath $taskSources[$taskIndex] -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskSourceExpected.sha256) { throw 'An operational input changed after baseline.' }
    Copy-Item -LiteralPath $taskSources[$taskIndex] -Destination $taskDestination
    $taskOriginalHash = (Get-FileHash -LiteralPath $taskSources[$taskIndex] -Algorithm SHA256).Hash.ToLowerInvariant()
    if ((Get-FileHash -LiteralPath $taskDestination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskOriginalHash) { throw 'Backup verification failed.' }
    $taskBackups += [pscustomobject]@{ original=$taskSources[$taskIndex]; backup=$taskDestination; sha256=$taskOriginalHash }
}
$taskRecord = [ordered]@{
    prepared_at=(Get-Date).ToString('o'); user_authorization='2026-10-18: finish 147, investigate stopped collection, continue resumable work in parallel';
    scope='Explicit manual stale-lock handover then one bounded 2-batch continuation; not old pending settlement';
    active_collectors_before=$taskCollectors; backups=$taskBackups;
    old_pending_reserved_bytes_preserved=136314880; old_pending_retry=$false; refund_bytes=0;
    new_batches_maximum=2; new_reservation_maximum_bytes=136314880;
    legacy_lock_original=$taskLock; legacy_lock_sha256=$taskExpectedLock.sha256;
    legacy_lock_archive=(Join-Path $taskBackup 'global-ledger.execution.lock');
    race_limit='Point-in-time OS inventory plus existing O_EXCL execution lock; no global OS process sandbox or atomic ledger/aggregate journal.';
    status='PREPARED'
}
$taskRecord | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $taskEvidence -Encoding utf8
$taskRecheckedCollectors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w|[0-9.]*)?\.exe$' -and $_.CommandLine -match 'collect_training_parallel\.py|collect_training_grid\.py|collect_samples\.py|monitor_collection_progress\.py'
})
if ($taskRecheckedCollectors.Count -ne 0) { throw 'A collector/monitor appeared during handover preparation.' }
if (Test-Path -LiteralPath $taskBudgetLock) { throw 'A budget transaction lock appeared.' }
if ((Get-FileHash -LiteralPath $taskLedger -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpected.sha256) { throw 'Ledger changed during preparation.' }
if ((Get-FileHash -LiteralPath $taskLock -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpectedLock.sha256) { throw 'Execution lock changed during preparation.' }
Move-Item -LiteralPath $taskLock -Destination $taskRecord.legacy_lock_archive
$taskRecord.status = 'LEGACY_LOCK_ARCHIVED'
$taskRecord | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $taskEvidence -Encoding utf8
$env:PYTHONPATH = "$taskRoot\.runtime;$taskRoot\backend;$taskRoot"
$env:PYTHONIOENCODING = 'utf-8'
$taskProcess = Start-Process -FilePath (Get-Command python).Source -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -ArgumentList @(
    'scripts/collect_training_parallel.py', '--candidate-plan', 'data/first-group-training-esri-v2/lane-b-candidates.json',
    '--continue-unrelated-pending', '--max-batches', '2', '--execute'
) -RedirectStandardOutput (Join-Path $PSScriptRoot 'collection-resume-live-20261018-stdout.log') -RedirectStandardError (Join-Path $PSScriptRoot 'collection-resume-live-20261018-stderr.log')
$taskRecord.status = 'BOUNDED_CONTINUATION_LAUNCHED'
$taskRecord.launched_at = (Get-Date).ToString('o')
$taskRecord.pid = $taskProcess.Id
$taskRecord | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $taskEvidence -Encoding utf8
Write-Output ('Bounded collector launched, PID ' + $taskProcess.Id + '; old pending reservations preserved.')
