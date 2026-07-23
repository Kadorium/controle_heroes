$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $env:RESET_EPIC_TEST_DATA) {
    Write-Host "Defina RESET_EPIC_TEST_DATA=1 para confirmar a limpeza operacional." -ForegroundColor Yellow
    Write-Host 'Exemplo: $env:RESET_EPIC_TEST_DATA="1"; .\scripts\reset_operational_test_data.ps1'
    exit 1
}

. .\.venv\Scripts\Activate.ps1 -ErrorAction SilentlyContinue

Write-Host "Backup opcional antes do reset..."
& "$Root\scripts\backup-db.ps1"

Write-Host "Executando reset operacional..."
python -m app.scripts.reset_operational_test_data --skip-backup
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Rodando pytest rápido pós-reset..."
python -m pytest tests/test_reset_operational.py tests/test_heroes_xlsx_parser.py -q
exit $LASTEXITCODE
