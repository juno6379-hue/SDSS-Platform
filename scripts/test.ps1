$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$env:PYTHONPATH = "$taskRoot\.runtime;$taskRoot\backend"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
