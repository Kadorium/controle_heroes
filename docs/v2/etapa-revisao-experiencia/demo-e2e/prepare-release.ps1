# One-shot preparation into a NEW directory/cluster. Never overwrites a release.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$epic=Split-Path $repo;$lab=Join-Path $epic 'audit-lab/stock-executive-20261023'
$release=Join-Path $epic 'audit-runtime/stock-executive-20261023'
$backup=Join-Path $epic ('backups/stock-executive-final-'+(Get-Date -Format yyyyMMdd-HHmmss))
$pg='C:/Program Files/PostgreSQL/18/bin'
if(Test-Path -LiteralPath $release){throw 'Release already exists; do not overwrite'}
if(Get-NetTCPConnection -LocalPort 5447 -State Listen -ErrorAction SilentlyContinue){throw '5447 occupied'}
$dirty=git -C $repo status --porcelain -- v2/app v2/frontend/src v2/alembic
if($dirty){throw 'Commit reviewed sources before preparing release'}
$identity=& "$pg/psql.exe" -h 127.0.0.1 -p 5445 -U postgres -d epic_v2_test -Atc "select current_database(),inet_server_port(),current_setting('data_directory')"
if($identity.Replace('\','/') -ne ('epic_v2_test|5445|'+(Join-Path $lab 'postgres').Replace('\','/'))){throw 'Wrong candidate database'}
New-Item -ItemType Directory -Path $backup,$release,"$release/v2","$release/v2/frontend"|Out-Null
& "$pg/pg_dump.exe" -h 127.0.0.1 -p 5445 -U postgres -d epic_v2_test -Fc -f "$backup/final.dump"
if($LASTEXITCODE -ne 0){throw 'pg_dump failed'}
& "$pg/pg_restore.exe" -l "$backup/final.dump"|Out-File "$backup/dump-list.txt" -Encoding utf8
& "$pg/pg_restore.exe" -f NUL "$backup/final.dump"
if($LASTEXITCODE -ne 0){throw 'dump parse failed'}
Copy-Item -LiteralPath "$lab/storage" -Destination "$backup/storage" -Recurse
Copy-Item -LiteralPath "$lab/scenario" -Destination "$backup/scenario" -Recurse
Copy-Item -LiteralPath "$repo/v2/frontend/dist" -Destination "$backup/dist" -Recurse
Copy-Item -LiteralPath "$repo/v2/app" -Destination "$release/v2/app" -Recurse
Copy-Item -LiteralPath "$repo/v2/alembic" -Destination "$release/v2/alembic" -Recurse
Copy-Item -LiteralPath "$repo/v2/requirements.txt","$repo/v2/alembic.ini" -Destination "$release/v2"
Copy-Item -LiteralPath "$repo/v2/frontend/dist" -Destination "$release/v2/frontend/dist" -Recurse
Copy-Item -LiteralPath "$lab/storage" -Destination "$release/storage" -Recurse
Copy-Item -LiteralPath "$PSScriptRoot/release-runtime.py" -Destination "$release/release-runtime.py"
Copy-Item -LiteralPath "$repo/v2/frontend/dist/assets/demo-manifest.json" -Destination "$release/demo-manifest.json"
& "$pg/initdb.exe" -D "$release/postgres" -U postgres --encoding=UTF8 --locale=C --auth=trust|Out-Null
if($LASTEXITCODE -ne 0){throw 'initdb failed'}
$ctl=Start-Process -FilePath "$pg/pg_ctl.exe" -ArgumentList '-D',"$release/postgres",'-l',"$release/postgres.log",'-o','"-p 5447 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$release/pg-start.log" -RedirectStandardError "$release/pg-start.err"
$ctl.WaitForExit();if($ctl.ExitCode -ne 0){throw 'PG start failed'}
$actual=& "$pg/psql.exe" -h 127.0.0.1 -p 5447 -U postgres -d postgres -Atc 'show data_directory'
if([IO.Path]::GetFullPath($actual) -ne [IO.Path]::GetFullPath("$release/postgres")){throw 'Wrong release database'}
& "$pg/createdb.exe" -h 127.0.0.1 -p 5447 -U postgres epic_v2_test
& "$pg/pg_restore.exe" -h 127.0.0.1 -p 5447 -U postgres -d epic_v2_test --no-owner --no-acl "$backup/final.dump"
if($LASTEXITCODE -ne 0){throw 'Restore into NEW release failed'}
$files=@();foreach($folder in @('v2/app','v2/frontend/dist','storage')){foreach($file in Get-ChildItem -LiteralPath (Join-Path $release $folder) -Recurse -File){if($file.Extension -ne '.pyc'){$files+=@{path=$file.FullName.Substring($release.Length+1);sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}}}}
$manifest=@{created=(Get-Date).ToString('o');source_commit=(git -C $repo rev-parse HEAD);backup=$backup;release=$release;dump_sha256=(Get-FileHash "$backup/final.dump" -Algorithm SHA256).Hash;files=$files}
$manifest|ConvertTo-Json -Depth 5|Set-Content "$release/release.json" -Encoding utf8
Copy-Item -LiteralPath "$release/release.json" -Destination "$backup/release.json"
Write-Output "Prepared $release; backup $backup. Old 8082/5433 unchanged."
