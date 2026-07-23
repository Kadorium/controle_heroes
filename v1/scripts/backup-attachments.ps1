$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$attachments = Join-Path $Root "data\attachments"
$backupDir = Join-Path $Root "backups\attachments"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zipFile = Join-Path $backupDir "attachments_$timestamp.zip"
$logFile = Join-Path $Root "logs\backup-attachments.log"

try {
    if (-not (Test-Path $attachments)) {
        New-Item -ItemType Directory -Force -Path $attachments | Out-Null
    }
    Compress-Archive -Path (Join-Path $attachments "*") -DestinationPath $zipFile -Force
    "[$timestamp] SUCCESS $zipFile" | Add-Content $logFile
    Write-Host "Backup anexos OK: $zipFile" -ForegroundColor Green
} catch {
    "[$timestamp] ERROR $_" | Add-Content $logFile
    Write-Error $_
}

Get-ChildItem $backupDir -Filter "*.zip" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force
