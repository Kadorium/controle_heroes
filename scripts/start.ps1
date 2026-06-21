$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Epic Importacoes - start ==" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Arquivo .env criado a partir de .env.example" -ForegroundColor Yellow
}

if (-not (Test-Path ".venv")) {
    Write-Host "Criando venv Python..."
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Instalando dependencias frontend..."
    Push-Location frontend
    npm install
    Pop-Location
}

Write-Host "Build frontend..."
Push-Location frontend
npm run build
Pop-Location

Write-Host "Migracoes Alembic..."
alembic upgrade head

$port = 8080
if (Test-Path ".env") {
    $match = Select-String -Path ".env" -Pattern "^PORT=(\d+)" | Select-Object -First 1
    if ($match) { $port = [int]$match.Matches.Groups[1].Value }
}

Write-Host "Servidor: http://127.0.0.1:$port" -ForegroundColor Green
Write-Host "Rede LAN: http://<IP-DO-SERVIDOR>:$port" -ForegroundColor Green

python -m uvicorn app.main:app --host 0.0.0.0 --port $port
