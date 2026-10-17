$processes = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|node' })
$observed = [ordered]@{
 observed_at = (Get-Date).ToString('o')
 listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 5173,5174,8000,8001,8002 } | Select-Object LocalPort,OwningProcess)
 api_processes = @($processes | Where-Object { $_.CommandLine -match 'uvicorn|spawn_main' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine)
 all_python_node_operation_candidates = @($processes | Where-Object { $_.CommandLine -match 'first.group|train_pipeline|collect_pipeline|readiness_qa|annual_window' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine)
 worker_observation_scope = 'Local Python/node command-line patterns only; no remote or hidden-worker assurance'
 automation_status = @((Get-Content 'C:/Users/최준오/.codex/automations/geoai-2/automation.toml' | Select-String '^status|^rrule').Line)
 non_reload_api_8000_8001_new_code_loaded = 'UNVERIFIED; processes retained, no restart or Job submission performed'
 reload_api_8002_new_code_loaded = '107 UNVERIFIED: reload setup alone is not behavior proof. Prior105 endpoint only was verified; no107 live requests performed.'
}
$observed | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 evidence/integration/workflow-dependency-order-runtime-start-20261017.json
$observed | ConvertTo-Json -Depth 6



