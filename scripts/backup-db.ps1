$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. .\.venv\Scripts\Activate.ps1 -ErrorAction SilentlyContinue

$envFile = Join-Path $Root ".env"
$dbUrl = "postgresql://postgres@localhost:5433/epic_importacao"
if (Test-Path $envFile) {
    $line = Select-String -Path $envFile -Pattern "^DATABASE_URL=(.+)$" | Select-Object -First 1
    if ($line) { $dbUrl = $line.Matches.Groups[1].Value.Trim() }
}

$backupDir = Join-Path $Root "backups\db"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $backupDir "epic_importacao_$timestamp.sql"
$logFile = Join-Path $Root "logs\backup-db.log"

try {
    & pg_dump $dbUrl -f $outFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump falhou com codigo $LASTEXITCODE" }
    "[$timestamp] SUCCESS $outFile" | Add-Content $logFile
    Write-Host "Backup DB OK: $outFile" -ForegroundColor Green
} catch {
    "[$timestamp] ERROR $_" | Add-Content $logFile
    Write-Error $_
}

# Retencao 30 dias
Get-ChildItem $backupDir -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force
