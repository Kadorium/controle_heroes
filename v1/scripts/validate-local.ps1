# Validacao local — release candidate Epic Importacoes
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

$failed = $false

try {
    Write-Step "pytest (backend)"
    & .\.venv\Scripts\pytest tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) { throw "pytest falhou ($LASTEXITCODE)" }
} catch {
    Write-Host "FALHA: $_" -ForegroundColor Red
    $failed = $true
}

try {
    Write-Step "npm run build (frontend)"
    Push-Location frontend
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "build falhou ($LASTEXITCODE)" }
    Pop-Location
} catch {
    if (Test-Path frontend) { Pop-Location -ErrorAction SilentlyContinue }
    Write-Host "FALHA: $_" -ForegroundColor Red
    $failed = $true
}

$healthUrl = "http://127.0.0.1:8082/api/health"
$serverUp = $false
try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
    $serverUp = $r.StatusCode -eq 200
} catch {
    $serverUp = $false
}

if ($serverUp) {
    try {
        Write-Step "Playwright E2E (servidor detectado em :8082)"
        Push-Location frontend
        $env:E2E_BASE_URL = "http://127.0.0.1:8082"
        npm run test:e2e
        if ($LASTEXITCODE -ne 0) { throw "E2E falhou ($LASTEXITCODE)" }
        Pop-Location
    } catch {
        if (Test-Path frontend) { Pop-Location -ErrorAction SilentlyContinue }
        Write-Host "FALHA: $_" -ForegroundColor Red
        $failed = $true
    }

    try {
        Write-Step "Health check"
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        if ($health.status -ne "ok") { throw "health status != ok" }
        Write-Host "Health OK: database=$($health.database)" -ForegroundColor Green
    } catch {
        Write-Host "FALHA health: $_" -ForegroundColor Red
        $failed = $true
    }
} else {
    Write-Host "`nAVISO: Servidor nao detectado em $healthUrl" -ForegroundColor Yellow
    Write-Host "Inicie com: .\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082" -ForegroundColor Yellow
    Write-Host "Depois rode novamente: powershell -File scripts\validate-local.ps1" -ForegroundColor Yellow
    Write-Host "E2E e health check foram PULADOS." -ForegroundColor Yellow
}

if ($failed) {
    Write-Host "`nVALIDACAO LOCAL: FALHOU" -ForegroundColor Red
    exit 1
}

Write-Host "`nVALIDACAO LOCAL: OK" -ForegroundColor Green
exit 0
