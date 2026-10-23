# Switch the local URL back; neither database is restored over or downgraded.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$old=Join-Path (Split-Path $repo) 'audit-runtime/pre-demo-ceo-20261022'
if(!(Test-Path -LiteralPath "$old/v2/frontend/dist/assets/build-info.json")){throw 'Previous full release missing'}
$oldBuild=Get-Content -LiteralPath "$old/v2/frontend/dist/assets/build-info.json" -Raw|ConvertFrom-Json
if($oldBuild.revision -ne 'experience-r2-integration-20261023.3'){throw 'Previous build differs; review preservation first'}
$active=Invoke-RestMethod http://127.0.0.1:8082/assets/build-info.json
if($active.build_id -ne 'stock-executive-20261023.1'){throw 'Unexpected current runtime; do not stop it'}
$owner=(Get-NetTCPConnection -LocalPort 8082 -State Listen).OwningProcess
$info=Get-CimInstance Win32_Process -Filter "ProcessId=$owner"
if($info.CommandLine -notmatch 'stock-executive-20261023.*release-runtime.py'){throw 'Unexpected owner of 8082'}
Stop-Process -Id $owner
& "$repo/docs/v2/etapa-pre-demo-ceo/scripts/start-audit-runtime.ps1" -Port 8082
Write-Output 'Previous source/dist/storage and schema031 database5433 restored by switching binding. Check /api/health and /assets/build-info.json. New database5447 remains preserved.'
