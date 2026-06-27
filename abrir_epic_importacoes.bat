@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set PORT=8080
set CONFIG_IP=%~dp0epic_server_ip.txt
set SERVER_IP=

if exist "%CONFIG_IP%" (
    for /f "usebackq eol=# tokens=* delims=" %%L in ("%CONFIG_IP%") do (
        set "SERVER_IP=%%L"
        goto :ip_from_config
    )
)
:ip_from_config

if defined SERVER_IP (
    echo Usando IP do servidor configurado em epic_server_ip.txt: %SERVER_IP%
    echo ^(Edite o arquivo ou apague-o para informar outro IP.^)
    echo.
) else (
    echo ============================================================
    echo   Epic Importacoes - Acesso na rede
    echo ============================================================
    echo.
    echo Informe o IP do PC servidor onde roda start_server.bat
    echo ^(ex.: 192.168.1.50^).
    echo.
    set /p SERVER_IP=IP do servidor: 
    if not defined SERVER_IP (
        echo ERRO: IP nao informado.
        pause
        exit /b 1
    )
    echo.
    set /p SAVE_IP=Salvar este IP em epic_server_ip.txt para proximas vezes? [S/N]: 
    if /i "!SAVE_IP!"=="S" (
        >"%CONFIG_IP%" echo !SERVER_IP!
        echo IP salvo em %CONFIG_IP%
    )
)

REM Remover espacos acidentais
for /f "tokens=* delims= " %%A in ("%SERVER_IP%") do set SERVER_IP=%%A

set URL=http://%SERVER_IP%:%PORT%/

echo Abrindo navegador em %URL%
start "" "%URL%"

exit /b 0
