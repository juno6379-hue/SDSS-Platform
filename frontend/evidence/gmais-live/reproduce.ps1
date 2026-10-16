# 로컬 계약 시험만 재현한다. 과학 추론·운영 데이터·모델 승인 요청은 포함하지 않는다.
$ErrorActionPreference = 'Stop'
$caseRoot = $PSScriptRoot
$jobCase = Get-Content -Raw -LiteralPath (Join-Path $caseRoot 'job.json') | ConvertFrom-Json
$requestKey = Get-Content -Raw -LiteralPath (Join-Path $caseRoot 'idempotency-key.txt')
curl.exe --silent --show-error --max-time 30 --dump-header (Join-Path $caseRoot 'replay-submit.headers.txt') --output (Join-Path $caseRoot 'replay-submit.json') -H 'Content-Type: application/json' -H "Idempotency-Key: $requestKey" --data-binary "@$(Join-Path $caseRoot 'blocked-request.json')" http://127.0.0.1:8000/v1/agents/lcluc-agent/jobs
curl.exe --silent --show-error --max-time 30 --dump-header (Join-Path $caseRoot 'replay-job.headers.txt') --output (Join-Path $caseRoot 'replay-job.json') "http://127.0.0.1:8000/v1/jobs/$($jobCase.job_id)"
curl.exe --silent --show-error --max-time 30 --dump-header (Join-Path $caseRoot 'replay-results.headers.txt') --output (Join-Path $caseRoot 'replay-results.json') "http://127.0.0.1:8000/v1/jobs/$($jobCase.job_id)/results"
# 계획 경로는 원본 OpenAPI의 일부가 아닌 내부 RFC 확장이며 실행을 시작하지 않는다.
curl.exe --silent --show-error --max-time 30 --dump-header (Join-Path $caseRoot 'replay-plan.headers.txt') --output (Join-Path $caseRoot 'replay-plan.json') -H 'Content-Type: application/json' --data-binary "@$(Join-Path $caseRoot 'browser-plan-request.json')" http://127.0.0.1:8000/v1/workflows/plan
