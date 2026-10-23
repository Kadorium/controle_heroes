param([ValidateSet(8082,8090)][int]$Port=8082)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$release=Join-Path (Split-Path $repo) 'audit-runtime/stock-executive-20261023'
$pg='C:/Program Files/PostgreSQL/18/bin'
if(!(Test-Path -LiteralPath "$release/release.json")){throw 'Verified release missing; startup never prepares data'}
if(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue){throw "Port $Port occupied; no process stopped"}
if(!(Get-NetTCPConnection -LocalPort 5447 -State Listen -ErrorAction SilentlyContinue)){
 $ctl=Start-Process -FilePath "$pg/pg_ctl.exe" -ArgumentList '-D',"$release/postgres",'-l',"$release/postgres.log",'-o','"-p 5447 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$release/restart-pg.log" -RedirectStandardError "$release/restart-pg.err";$ctl.WaitForExit();if(!(Get-NetTCPConnection -LocalPort 5447 -State Listen -ErrorAction SilentlyContinue)){throw 'PG start failed'}
}
$p=Start-Process -FilePath "$repo/v2/.venv/Scripts/python.exe" -ArgumentList "$release/release-runtime.py",$release,$Port -WorkingDirectory $release -WindowStyle Hidden -PassThru -RedirectStandardOutput "$release/runtime-$Port.out" -RedirectStandardError "$release/runtime-$Port.err"
Write-Output "Started PID $($p.Id) on http://127.0.0.1:$Port; no seed/reset/build."
