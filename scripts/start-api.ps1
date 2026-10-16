param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
# 로컬 시험 설치 경로도 지원하며 기본 수신 주소는 루프백으로 제한한다.
$env:PYTHONPATH = "$taskRoot\.runtime;$taskRoot\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
