param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$envFile = Join-Path $Root ".env"
$dbUrl = "postgresql://postgres@localhost:5433/epic_importacao"
if (Test-Path $envFile) {
    $line = Select-String -Path $envFile -Pattern "^DATABASE_URL=(.+)$" | Select-Object -First 1
    if ($line) { $dbUrl = $line.Matches.Groups[1].Value.Trim() }
}

if (-not (Test-Path $BackupFile)) {
    Write-Error "Arquivo de backup nao encontrado: $BackupFile"
}

Write-Host "Restaurando $BackupFile ..."
& psql $dbUrl -f $BackupFile
if ($LASTEXITCODE -ne 0) { Write-Error "psql restore falhou" }
Write-Host "Restore concluido." -ForegroundColor Green
