param(
    [switch]$Sample,
    [switch]$Offline,
    [ValidateRange(1, 512)][int]$WindowSize = 64,
    [string]$Python = "python",
    [string]$Endpoint = "earth-search"
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    # mock 계약검증과 실네트워크 검증을 별도 실행하여 실패 원인을 구별한다.
    & $Python -m unittest discover -s tests -p "test_data*.py" -v
    if ($LASTEXITCODE -ne 0) { throw "수집 계약 테스트 실패. 네트워크 진단 전에 코드 실패를 해결하세요." }
    $diagnosticArguments = @("scripts/diagnose_stac.py", "--window-size", "$WindowSize", "--endpoint", $Endpoint)
    if ($Sample) { $diagnosticArguments += "--sample" }
    if ($Offline) { $diagnosticArguments += "--offline" }
    & $Python @diagnosticArguments
    $diagnosticExit = $LASTEXITCODE
    Write-Host "진단 결과: data/validation/diagnosis.json"
    exit $diagnosticExit
}
finally { Pop-Location }
