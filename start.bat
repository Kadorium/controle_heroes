@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo == Epic Importacoes - start ==
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERRO: ambiente nao instalado. Execute install.bat primeiro.
    pause
    exit /b 1
)

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Arquivo .env criado a partir de .env.example
)

set PORT=8080
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /r /b "^PORT=" ".env" 2^>nul`) do set PORT=%%B

call ".venv\Scripts\activate.bat"

echo Build frontend...
pushd frontend
call npm run build
if errorlevel 1 (
    popd
    echo ERRO: build frontend falhou.
    pause
    exit /b 1
)
popd

echo Migracoes Alembic...
call alembic upgrade head
if errorlevel 1 (
    echo ERRO: migracoes falharam.
    pause
    exit /b 1
)

echo Servidor: http://127.0.0.1:%PORT%
echo Rede LAN: http://^<IP-DO-SERVIDOR^>:%PORT%
echo.

start "Epic Importacoes - Servidor" cmd /k "cd /d "%~dp0." && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%"

echo Aguardando servidor e abrindo navegador...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$port = '%PORT%'; $url = 'http://127.0.0.1:' + $port; for ($i = 0; $i -lt 60; $i++) { try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { Start-Process $url; exit 0 } } catch {}; Start-Sleep -Seconds 1 }; Start-Process $url"

exit /b 0
