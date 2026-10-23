param([switch]$RecoverPrevious)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$epic=Split-Path $repo
$expected=if($RecoverPrevious){Join-Path $epic 'audit-runtime/receiving-stock-20261023'}else{Join-Path $epic 'audit-runtime/laptop-prices-20261023'}
$listeners=@(Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue)
foreach($listener in $listeners){
 $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
 if(!$process.CommandLine -or !$process.CommandLine.Contains($expected) -or !$process.CommandLine.Contains('release-runtime.py')){throw '8082 is not the expected release; no process stopped'}
 Stop-Process -Id $listener.OwningProcess
}
if($RecoverPrevious){& "$PSScriptRoot/../laptop-round/start-release.ps1" -Port 8082}else{& "$PSScriptRoot/start-release.ps1" -Port 8082}
Write-Output 'Only the verified HTTP process was replaced. Both databases/storage/releases retained. No restore/migration/seed.'
