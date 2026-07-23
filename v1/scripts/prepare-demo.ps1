# Prepara ambiente demo local (migracoes + seed 16 cenarios).
param(
    [switch]$ForceReseed
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Epic Importacoes — prepare-demo" -ForegroundColor Cyan

if ($ForceReseed) {
    Write-Host "AVISO: -ForceReseed solicitado. Isso adiciona/atualiza massa DEMO via API seed." -ForegroundColor Yellow
    Write-Host "Nao apaga dados reais automaticamente. Revise POs DEMO-* antes em producao." -ForegroundColor Yellow
}

Write-Host "`n1. Alembic upgrade head..."
& .\.venv\Scripts\alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Error "alembic upgrade falhou" }

Write-Host "`n2. Build frontend (opcional para servir UI atualizada)..."
Push-Location frontend
npm run build
Pop-Location

$port = 8082
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    $pl = Select-String -Path $envFile -Pattern "^PORT=(.+)$" | Select-Object -First 1
    if ($pl) { $port = $pl.Matches.Groups[1].Value.Trim() }
}

Write-Host "`n3. Seed demo (requer servidor rodando)..."
$base = "http://127.0.0.1:$port"
try {
    $login = Invoke-WebRequest -Uri "$base/api/auth/login" -Method POST -Body (@{
        email = "admin@epic.com.br"; password = "admin123"
    } | ConvertTo-Json) -ContentType "application/json" -SessionVariable sess -UseBasicParsing -TimeoutSec 5
    $seed = Invoke-WebRequest -Uri "$base/api/demo/seed" -Method POST -WebSession $sess -UseBasicParsing -TimeoutSec 120
    Write-Host "Seed demo OK" -ForegroundColor Green
} catch {
    Write-Host "Seed pulado — inicie o servidor e rode:" -ForegroundColor Yellow
    Write-Host "  POST $base/api/demo/seed (autenticado como admin)" -ForegroundColor Yellow
}

Write-Host "`n--- Pronto ---" -ForegroundColor Green
Write-Host "URL local: http://127.0.0.1:$port/"
Write-Host "Login dev: admin@epic.com.br / admin123"
Write-Host "ALTERE credenciais antes de uso em producao na Epic." -ForegroundColor Yellow
Write-Host "Iniciar servidor: .\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port $port"
