@echo off
REM ==============================================================
REM  LEAD MACHINE - Stop script
REM  Fecha Paperclip backend + serve.py (janelas do cmd tituladas)
REM ==============================================================

echo.
echo [Lead Machine] Parando processos...
echo.

REM Fecha as janelas tituladas do start.bat
taskkill /FI "WINDOWTITLE eq Paperclip Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Lead Machine Dashboard*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Lead Machine Runner*" /T /F >nul 2>&1

REM Garante que nao fica porta presa - mata qualquer node/tsx/python que esteja usando 3100/8081
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :3100 ^| findstr LISTENING') do (
    echo Matando PID %%P (porta 3100)
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8081 ^| findstr LISTENING') do (
    echo Matando PID %%P (porta 8081)
    taskkill /PID %%P /F >nul 2>&1
)

echo.
echo [Lead Machine] Parado.
echo.
