@echo off
REM ==============================================================
REM  LEAD MACHINE - Stop script
REM  Fecha Paperclip backend + serve.py (janelas do cmd tituladas)
REM ==============================================================

setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "PAPERCLIP_PORT=3100"
set "DASHBOARD_PORT=8081"
call :load_env

echo.
echo [Lead Machine] Parando processos...
echo.

REM Fecha as janelas tituladas do start.bat
taskkill /FI "WINDOWTITLE eq Paperclip Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Lead Machine Frontend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Lead Machine Dashboard*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Lead Machine Runner*" /T /F >nul 2>&1

REM Garante que nao fica porta presa.
call :kill_port %PAPERCLIP_PORT%
if not "%PAPERCLIP_PORT%"=="3100" call :kill_port 3100
call :kill_port %DASHBOARD_PORT%
if not "%DASHBOARD_PORT%"=="8081" call :kill_port 8081

echo.
echo [Lead Machine] Parado.
echo.
endlocal
exit /b 0

:load_env
if not exist "%ROOT%.env" exit /b 0
for /f "tokens=1,* delims==" %%A in ('findstr /B /I /C:"PAPERCLIP_PORT=" /C:"DASHBOARD_PORT=" "%ROOT%.env" 2^>nul') do (
    set "ENV_KEY=%%~A"
    set "ENV_VALUE=%%~B"
    if /i "!ENV_KEY!"=="PAPERCLIP_PORT" set "PAPERCLIP_PORT=!ENV_VALUE!"
    if /i "!ENV_KEY!"=="DASHBOARD_PORT" set "DASHBOARD_PORT=!ENV_VALUE!"
)
exit /b 0

:kill_port
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%~1" ^| findstr LISTENING') do (
    echo Matando PID %%P (porta %~1)
    taskkill /PID %%P /F >nul 2>&1
)
exit /b 0
