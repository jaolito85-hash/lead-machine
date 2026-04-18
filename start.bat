@echo off
REM ==============================================================
REM  LEAD MACHINE - Start script
REM  Sobe Paperclip backend + serve.py + abre dashboard no browser
REM  Log completo em: %ROOT%start.log
REM ==============================================================

setlocal EnableDelayedExpansion
set ROOT=%~dp0
set PAPERCLIP_URL=http://localhost:3100
set DASHBOARD_URL=http://localhost:8081
set MAX_TRIES=120
set LOG=%ROOT%start.log

REM Limpa log antigo
echo [%date% %time%] start.bat iniciado > "%LOG%"

call :log [Lead Machine] Iniciando...

REM -- Checagem de dependencias --
call :check_dep pnpm "npm install -g pnpm"
if errorlevel 1 goto fatal
call :check_dep node "baixe em https://nodejs.org"
if errorlevel 1 goto fatal
call :check_dep python "baixe em https://python.org"
if errorlevel 1 goto fatal
call :check_dep curl "normalmente vem com Windows 10+"
if errorlevel 1 goto fatal

REM -- Checar se porta 3100 ja esta ocupada --
netstat -ano | findstr :3100 | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    call :log [AVISO] Porta 3100 ja ocupada. Se for uma instancia antiga, rode stop.bat antes.
)

REM 1) Paperclip backend (janela separada)
call :log [1/3] Subindo Paperclip backend em janela separada...
start "Paperclip Backend" cmd /k "cd /d %ROOT%paperclip && pnpm dev"

REM 2) Espera o Paperclip responder
call :log [2/3] Aguardando Paperclip ficar UP em %PAPERCLIP_URL% (ate %MAX_TRIES%s) ...
set /a TRIES=0
:waitpaperclip
set /a TRIES+=1
if !TRIES! GTR %MAX_TRIES% goto timeout_paperclip
curl -s -o nul -w "%%{http_code}" %PAPERCLIP_URL%/api/companies > "%TEMP%\lm_check.txt" 2>nul
set /p STATUS=<"%TEMP%\lm_check.txt"
if "!STATUS!"=="200" goto paperclipup
set /a MOD=!TRIES! %% 10
if !MOD!==0 call :log       ... ainda aguardando (!TRIES!s / status=!STATUS!)
ping -n 2 127.0.0.1 >nul
goto waitpaperclip

:paperclipup
call :log       OK - Paperclip online em !TRIES!s.

REM 3) Dashboard + proxy
call :log [3/3] Subindo dashboard em %DASHBOARD_URL% ...
start "Lead Machine Dashboard" cmd /k "cd /d %ROOT% && python serve.py"

REM Pequena espera para o serve.py abrir a porta
ping -n 3 127.0.0.1 >nul

REM Abre browser
start "" %DASHBOARD_URL%

call :log.
call :log =============================================================
call :log  TUDO PRONTO
call :log  Dashboard: %DASHBOARD_URL%
call :log  Paperclip: %PAPERCLIP_URL%
call :log.
call :log  Para parar tudo: rode stop.bat ou feche as 2 janelas abertas.
call :log =============================================================
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
endlocal
exit /b 0

REM ==============================================================
REM SUB-ROUTINES
REM ==============================================================

:log
echo %*
echo [%time%] %* >> "%LOG%"
exit /b 0

:check_dep
where %~1 >nul 2>&1
if errorlevel 1 (
    call :log [ERRO] %~1 nao encontrado no PATH.
    call :log        Instalacao: %~2
    exit /b 1
)
for /f "delims=" %%v in ('where %~1') do (
    call :log       OK %~1 em %%v
    goto :check_dep_done
)
:check_dep_done
exit /b 0

:timeout_paperclip
call :log.
call :log ================================================================
call :log  [ERRO] Paperclip nao respondeu em %MAX_TRIES%s.
call :log.
call :log  Olhe a janela "Paperclip Backend" - ela tem o erro real.
call :log  Causas comuns:
call :log   - Primeira execucao: rode 'pnpm install' em %ROOT%paperclip
call :log   - Porta 3100 em uso
call :log   - Erro de build
call :log  Teste manual: cd /d %ROOT%paperclip ^&^& pnpm dev
call :log ================================================================
goto fatal

:fatal
echo.
echo Log completo em: %LOG%
echo Pressione qualquer tecla para fechar...
pause >nul
endlocal
exit /b 1
