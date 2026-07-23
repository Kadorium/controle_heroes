# Registra tarefa diaria de backup no Windows Task Scheduler (requer admin).
param(
    [string]$TaskName = "EpicImportacao-BackupDiario",
    [string]$RunTime = "02:00"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dailyScript = Join-Path $PSScriptRoot "backup-daily.ps1"
$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $dailyScript)) {
    Write-Error "Script nao encontrado: $dailyScript"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$dailyScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At $RunTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Atualizando tarefa existente: $TaskName" -ForegroundColor Yellow
    Set-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
} else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Backup diario DB + anexos Epic Importacoes" | Out-Null
}

Write-Host "Tarefa registrada: $TaskName as $RunTime" -ForegroundColor Green
Write-Host "Executa: backup-daily.ps1 (DB + anexos, retencao 30d, logs em logs/)" -ForegroundColor Green
Write-Host "Teste manual: powershell -File scripts\backup-daily.ps1" -ForegroundColor Cyan
Write-Host "Requer PowerShell como Administrador para Register-ScheduledTask." -ForegroundColor Yellow
