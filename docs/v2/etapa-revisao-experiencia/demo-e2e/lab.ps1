$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$epic=Split-Path $repo
$lab=Join-Path $epic 'audit-lab/stock-executive-20261023'
$pg='C:/Program Files/PostgreSQL/18/bin'
$data=Join-Path $lab 'postgres'
New-Item -ItemType Directory -Force -Path $lab|Out-Null
if(!(Test-Path -LiteralPath $data)) {
 if(Get-NetTCPConnection -LocalPort 5445 -State Listen -ErrorAction SilentlyContinue){throw 'Port 5445 occupied'}
 & "$pg/initdb.exe" -D $data -U postgres --encoding=UTF8 --locale=C --auth=trust|Out-Null
 if($LASTEXITCODE -ne 0){throw 'initdb failed'}
}
if(!(Get-NetTCPConnection -LocalPort 5445 -State Listen -ErrorAction SilentlyContinue)){
 $p=Start-Process -FilePath "$pg/pg_ctl.exe" -ArgumentList '-D',$data,'-l',"$lab/postgres.log",'-o','"-p 5445 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$lab/pg-start.out" -RedirectStandardError "$lab/pg-start.err"
 $p.WaitForExit()
}
$actual=& "$pg/psql.exe" -h 127.0.0.1 -p 5445 -U postgres -d postgres -Atc 'show data_directory'
if([IO.Path]::GetFullPath($actual) -ne [IO.Path]::GetFullPath($data)){throw 'Wrong lab cluster'}
$exists=& "$pg/psql.exe" -h 127.0.0.1 -p 5445 -U postgres -d postgres -Atc "select 1 from pg_database where datname='epic_v2_test'"
if($exists -ne '1'){
 & "$pg/createdb.exe" -h 127.0.0.1 -p 5445 -U postgres epic_v2_test
 & "$pg/pg_restore.exe" -h 127.0.0.1 -p 5445 -U postgres -d epic_v2_test --no-owner --no-acl "$epic/backups/integration-20261023-114731/demo-before.dump"
 if($LASTEXITCODE -ne 0){throw 'Restore to NEW lab failed'}
}
if(!(Test-Path -LiteralPath "$lab/storage")){Copy-Item -LiteralPath "$epic/audit-runtime/pre-demo-ceo-20261022/demo-storage" -Destination "$lab/storage" -Recurse}
& "$pg/psql.exe" -h 127.0.0.1 -p 5445 -U postgres -d epic_v2_test -Atc "select current_database(),inet_server_port(),system_identifier from pg_control_system()"
Write-Output "Candidate: 8088; database 5445; storage $lab/storage. No reset or changes to 8082."
