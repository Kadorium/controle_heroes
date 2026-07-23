$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "backup-db.ps1")
& (Join-Path $PSScriptRoot "backup-attachments.ps1")
Write-Host "Backup diario concluido." -ForegroundColor Green
