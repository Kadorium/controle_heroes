@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo == Epic Importacoes - install ==
echo.

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Arquivo .env criado a partir de .env.example
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando venv Python...
    python -m venv .venv
    if errorlevel 1 (
        echo ERRO: falha ao criar venv. Verifique se Python esta instalado.
        pause
        exit /b 1
    )
)

echo Instalando dependencias Python...
call ".venv\Scripts\activate.bat"
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERRO: pip install falhou.
    pause
    exit /b 1
)

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
) else (
    echo Dependencias frontend ja instaladas.
)

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
    echo ERRO: migracoes falharam. Verifique PostgreSQL e DATABASE_URL no .env
    pause
    exit /b 1
)

echo.
echo Instalacao concluida. Use start_server.bat (servidor LAN) ou start.bat (dev local).
pause
