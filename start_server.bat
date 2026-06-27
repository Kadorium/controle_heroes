@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   Epic Importacoes - Servidor (PC servidor da rede)
echo ============================================================
echo.

if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo Arquivo .env criado a partir de .env.example
    ) else (
        echo ERRO: .env.example nao encontrado.
        pause
        exit /b 1
    )
)

set PORT=8080
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /r /b "^PORT=" ".env" 2^>nul`) do set PORT=%%B
if not defined PORT set PORT=8080

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo ERRO: venv nao encontrado. Execute install.bat neste PC servidor primeiro.
    pause
    exit /b 1
)

set DO_BUILD=0
if /i "%~1"=="rebuild" set DO_BUILD=1
if not exist "frontend\dist\index.html" set DO_BUILD=1

if "%DO_BUILD%"=="1" (
    echo Build frontend...
    if not exist "frontend\node_modules" (
        echo Instalando dependencias frontend...
        pushd frontend
        call npm install
        if errorlevel 1 (
            popd
            echo ERRO: npm install falhou.
            pause
            exit /b 1
        )
        popd
    )
    pushd frontend
    call npm run build
    if errorlevel 1 (
        popd
        echo ERRO: build frontend falhou.
        pause
        exit /b 1
    )
    popd
) else (
    echo Frontend dist OK. Use "start_server.bat rebuild" para forcar novo build.
)

echo Migracoes Alembic...
call alembic upgrade head
if errorlevel 1 (
    echo ERRO: migracoes falharam. Verifique PostgreSQL local e DATABASE_URL no .env
    echo        PostgreSQL deve permanecer apenas em localhost ^(nao exposto na rede^).
    pause
    exit /b 1
)

echo.
echo PostgreSQL: acesso apenas local ^(localhost^) — porta 5433 nao e exposta na rede LAN.
echo.

REM --- Firewall Windows (requer Administrador) ---
set FW_OK=0
net session >nul 2>&1
if errorlevel 1 (
    echo AVISO: Este script NAO esta em modo Administrador.
    echo         Nao foi possivel configurar o Firewall do Windows automaticamente.
    echo         Libere manualmente a porta TCP %PORT% ^(entrada^) ou execute como Administrador.
    echo.
) else (
    set RULE_NAME=Epic Importacoes HTTP %PORT%
    netsh advfirewall firewall show rule name="!RULE_NAME!" >nul 2>&1
    if errorlevel 1 (
        echo Configurando regra de firewall para porta TCP %PORT%...
        netsh advfirewall firewall add rule name="!RULE_NAME!" dir=in action=allow protocol=TCP localport=%PORT%
        if errorlevel 1 (
            echo AVISO: Falha ao criar regra de firewall ^(netsh retornou erro^).
            echo         Libere manualmente a porta TCP %PORT% no Firewall do Windows.
        ) else (
            echo Regra de firewall criada: !RULE_NAME!
            set FW_OK=1
        )
    ) else (
        echo Regra de firewall ja existe: !RULE_NAME!
        set FW_OK=1
    )
)

REM --- Detectar IP local na LAN (ipconfig — sem dependencia de PowerShell) ---
set SERVER_IP=NAO_DETECTADO
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "_IP=%%a"
    set "_IP=!_IP: =!"
    echo !_IP! | findstr /r "^169\.254\." >nul
    if errorlevel 1 (
        echo !_IP! | findstr /r "^127\." >nul
        if errorlevel 1 set SERVER_IP=!_IP!
    )
)

echo ============================================================
echo   Servidor pronto para iniciar
echo ============================================================
echo   Acesso neste PC:     http://127.0.0.1:%PORT%/
echo   IP local detectado:  %SERVER_IP%
if /i not "%SERVER_IP%"=="NAO_DETECTADO" (
    echo.
    echo   Outros computadores da rede devem acessar: http://%SERVER_IP%:%PORT%
) else (
    echo.
    echo   AVISO: IP local nao detectado automaticamente.
    echo   Outros computadores da rede devem acessar: http://^<IP_DO_SERVIDOR^>:%PORT%
    echo   Use "ipconfig" para descobrir o IPv4 deste PC.
)
if "%FW_OK%"=="0" (
    echo.
    echo   PENDENTE: confirme que a porta TCP %PORT% esta liberada no firewall.
)
echo ============================================================
echo.
echo Iniciando Uvicorn em 0.0.0.0:%PORT% ^(Ctrl+C para parar^)...
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

echo.
echo Servidor encerrado.
pause
