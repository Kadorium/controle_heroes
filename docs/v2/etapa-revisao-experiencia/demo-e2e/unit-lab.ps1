$ErrorActionPreference='Stop'
$lab='C:\Users\ricar\Desktop\projetos\EPIC\audit-lab\stock-executive-20261023'
$work='C:\Users\ricar\Desktop\projetos\EPIC\Controle'
$data=Join-Path $lab 'postgres-unit-5448'
$pg='C:\Program Files\PostgreSQL\18\bin'
if(!(Test-Path -LiteralPath $data)) {
 if(Get-NetTCPConnection -LocalPort 5448 -State Listen -ErrorAction SilentlyContinue){throw 'Port occupied'}
 & "$pg\initdb.exe" -D $data -U postgres --encoding=UTF8 --locale=C --auth=trust | Out-Null
 if($LASTEXITCODE -ne 0){throw 'initdb failed'}
}
if(!(Get-NetTCPConnection -LocalPort 5448 -State Listen -ErrorAction SilentlyContinue)){
 $ctl=Start-Process -FilePath "$pg\pg_ctl.exe" -ArgumentList '-D',$data,'-l',(Join-Path $lab 'unit-5448-pg.log'),'-o','"-p 5448 -h 127.0.0.1"','-w','start' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $lab 'unit-5448-pg-ctl.log') -RedirectStandardError (Join-Path $lab 'unit-5448-pg-ctl.err')
 $ctl.WaitForExit();if(!(Get-NetTCPConnection -LocalPort 5448 -State Listen -ErrorAction SilentlyContinue)){throw 'PG start failed'}
}
$cluster=& "$pg\psql.exe" -h 127.0.0.1 -p 5448 -U postgres -d postgres -Atc "SHOW data_directory;"
if($cluster.Replace('\','/') -ne $data.Replace('\','/')){throw 'Wrong unit cluster'}
$exists=& "$pg\psql.exe" -h 127.0.0.1 -p 5448 -U postgres -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='epic_v2_test';"
if($exists -ne '1'){& "$pg\createdb.exe" -h 127.0.0.1 -p 5448 -U postgres epic_v2_test;if($LASTEXITCODE -ne 0){throw 'new database failed'}}
$id=& "$pg\psql.exe" -h 127.0.0.1 -p 5448 -U postgres -d epic_v2_test -Atc "SELECT current_database(),inet_server_port(),current_setting('data_directory'),system_identifier FROM pg_control_system();"
if($id -notmatch 'epic_v2_test\|5448\|.*stock-executive-20261023/postgres-unit-5448\|'){throw "Unit identity mismatch: $id"}
$id | Set-Content -Encoding UTF8 (Join-Path $lab 'unit-final-identity.txt')
$env:TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:5448/epic_v2_test'
$env:DATABASE_URL=$env:TEST_DATABASE_URL
$env:APP_ENV='test'
Push-Location (Join-Path $work 'v2')
try { & '.\.venv\Scripts\python.exe' -m pytest tests/test_stock_executive.py tests/test_experience_reads.py tests/test_painel_ux2.py tests/test_reporting_dashboard.py -q --tb=short *> (Join-Path $lab 'backend-final.log'); $result=$LASTEXITCODE; Get-Content (Join-Path $lab 'backend-final.log') -Tail 25; if($result -ne 0){throw 'Unit gates failed'} } finally { Pop-Location }
