$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$epic=Split-Path $repo
$lab=Join-Path $epic 'audit-lab/integrated-20261023'
$old=Join-Path $epic 'audit-runtime/receiving-stock-20261023'
$backup=Get-ChildItem -LiteralPath (Join-Path $epic 'backups') -Directory -Filter 'integrated-before-*'|Sort-Object Name -Descending|Select-Object -First 1
if(!$backup -or !(Test-Path "$($backup.FullName)/preservation.json")){throw 'Verified backup required'}
if((Test-Path -LiteralPath $lab) -or (Get-NetTCPConnection -LocalPort 5452,8094 -State Listen -ErrorAction SilentlyContinue)){throw 'Lab destination/ports already exist'}
$pg='C:/Program Files/PostgreSQL/18/bin'
New-Item -ItemType Directory -Path $lab,"$lab/evidence"|Out-Null
Copy-Item -LiteralPath "$old/storage" -Destination "$lab/storage" -Recurse
Copy-Item -LiteralPath "$old/v2" -Destination "$lab/v2" -Recurse
Copy-Item -LiteralPath "$old/demo-manifest.json" -Destination "$lab/demo-manifest.json"
& "$pg/initdb.exe" -D "$lab/postgres" -U postgres --encoding=UTF8 --locale=C --auth=trust|Out-Null
if($LASTEXITCODE -ne 0){throw 'initdb failed'}
$ctl=Start-Process -FilePath "$pg/pg_ctl.exe" -ArgumentList '-D',"$lab/postgres",'-l',"$lab/postgres.log",'-o','"-p 5452 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$lab/pg-start.log" -RedirectStandardError "$lab/pg-start.err"
$ctl.WaitForExit()
$actual=& "$pg/psql.exe" -h 127.0.0.1 -p 5452 -U postgres -d postgres -Atc 'show data_directory'
if([IO.Path]::GetFullPath($actual) -ne [IO.Path]::GetFullPath("$lab/postgres")){throw 'Wrong cluster'}
& "$pg/createdb.exe" -h 127.0.0.1 -p 5452 -U postgres epic_v2_test
& "$pg/pg_restore.exe" -h 127.0.0.1 -p 5452 -U postgres -d epic_v2_test --no-owner --no-acl "$($backup.FullName)/presentation.dump"
if($LASTEXITCODE -ne 0){throw 'Restore failed'}
Write-Output "Isolated lab $lab / 5452, restored from $($backup.FullName). 8082/5451 untouched."
