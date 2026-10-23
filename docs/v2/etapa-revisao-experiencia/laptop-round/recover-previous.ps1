# Recover the intact pre-laptop release, not a historical Git checkout. No data restore.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$old=Join-Path (Split-Path $repo) 'audit-runtime/stock-executive-20261023'
if(!(Test-Path -LiteralPath "$old/release.json")){throw 'Previous release missing'}
$listener=Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue
if($listener){
 $owner=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
 if($owner.CommandLine -notlike '*laptop-prices-20261023*release-runtime.py*'){throw '8082 belongs to another runtime; nothing stopped'}
 Stop-Process -Id $listener.OwningProcess
}
& (Join-Path $PSScriptRoot '../demo-e2e/start-release.ps1') -Port 8082
Write-Output 'Previous code/dist/manifest/storage and DB 5447 recovered. New release/DB 5449 kept for diagnosis. Open http://127.0.0.1:8082/dashboard.'
