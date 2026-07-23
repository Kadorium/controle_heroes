$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$testDb = $env:TEST_DATABASE_URL
if (-not $testDb) { $testDb = "postgresql://postgres@localhost:5433/epic_importacao_test" }

Write-Host "== test-restore (DB de teste) ==" -ForegroundColor Cyan
& "$PSScriptRoot\backup-db.ps1"
$latest = Get-ChildItem (Join-Path $Root "backups\db") -Filter "*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) { Write-Error "Nenhum backup encontrado" }

Write-Host "Drop/create database de teste via psql..."
$adminUrl = $testDb -replace "/epic_importacao_test", "/postgres"
& psql $adminUrl -c "DROP DATABASE IF EXISTS epic_importacao_test;"
& psql $adminUrl -c "CREATE DATABASE epic_importacao_test;"
& psql $testDb -f $latest.FullName
if ($LASTEXITCODE -ne 0) { Write-Error "Restore de teste falhou" }
Write-Host "test-restore OK usando $($latest.Name)" -ForegroundColor Green
