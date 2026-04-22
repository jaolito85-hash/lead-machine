@echo off
REM ==============================================================
REM  LEAD MACHINE - Start script
REM  Sobe backend Paperclip + frontend Dashboard + runner local.
REM  Uso:
REM    start.bat          inicia tudo
REM    start.bat --check  valida dependencias sem abrir processos
REM ==============================================================

setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "LOG=%ROOT%start.log"
set "MAX_TRIES=120"
set "PAPERCLIP_PORT=3100"
set "DASHBOARD_PORT=8081"
set "START_GENERIC_RUNNER=0"
set "START_APOSTAS_RUNNER=0"
set "CHECK_ONLY=0"

if /i "%~1"=="--check" set "CHECK_ONLY=1"
if /i "%~1"=="/check" set "CHECK_ONLY=1"

echo [%date% %time%] start.bat iniciado > "%LOG%"
call :load_env

set "PORT=%PAPERCLIP_PORT%"
set "PAPERCLIP_URL=http://localhost:%PAPERCLIP_PORT%"
set "DASHBOARD_URL=http://localhost:%DASHBOARD_PORT%"

call :log [Lead Machine] Iniciando...
call :log       ROOT=%ROOT%
call :log       Paperclip=%PAPERCLIP_URL%
call :log       Dashboard=%DASHBOARD_URL%

REM -- Checagem de dependencias --
call :check_dep node "baixe em https://nodejs.org"
if errorlevel 1 goto :fatal
call :check_dep curl.exe "normalmente vem com Windows 10+"
if errorlevel 1 goto :fatal
call :resolve_pnpm
if errorlevel 1 goto :fatal
call :resolve_python
if errorlevel 1 goto :fatal
call :ensure_python_deps
if errorlevel 1 goto :fatal

if "%CHECK_ONLY%"=="1" (
    call :log [CHECK] Dependencias e configuracao basica OK.
    echo.
    echo Check concluido. Nada foi iniciado.
    endlocal
    exit /b 0
)

set "BACKEND_ALREADY_UP=0"
set "FRONTEND_ALREADY_UP=0"

REM -- Evita subir por cima de porta ocupada por outro processo --
call :is_port_listening %PAPERCLIP_PORT%
if not errorlevel 1 (
    call :check_http "%PAPERCLIP_URL%/api/health"
    if not errorlevel 1 (
        set "BACKEND_ALREADY_UP=1"
        call :log [AVISO] Backend ja esta online em %PAPERCLIP_URL%.
    ) else (
        call :log [ERRO] Porta %PAPERCLIP_PORT% ocupada, mas %PAPERCLIP_URL%/api/health nao respondeu.
        call :log        Rode stop.bat ou libere a porta antes de iniciar.
        goto :fatal
    )
)

call :is_port_listening %DASHBOARD_PORT%
if not errorlevel 1 (
    call :check_http "%DASHBOARD_URL%/"
    if not errorlevel 1 (
        set "FRONTEND_ALREADY_UP=1"
        call :log [AVISO] Frontend ja esta online em %DASHBOARD_URL%.
    ) else (
        call :log [ERRO] Porta %DASHBOARD_PORT% ocupada, mas o dashboard nao respondeu.
        call :log        Rode stop.bat ou libere a porta antes de iniciar.
        goto :fatal
    )
)

REM 1) Backend Paperclip (API + board UI em dev middleware)
if "%BACKEND_ALREADY_UP%"=="0" (
    call :log [1/4] Subindo backend Paperclip...
    start "Paperclip Backend" /D "%ROOT%paperclip" cmd /k "%PNPM_RUN% dev"
) else (
    call :log [1/4] Backend Paperclip reaproveitado.
)

REM 2) Espera o backend responder
call :log [2/4] Aguardando backend em %PAPERCLIP_URL%/api/health (ate %MAX_TRIES%s)...
set /a TRIES=0
:waitpaperclip
set /a TRIES+=1
if !TRIES! GTR %MAX_TRIES% goto :timeout_paperclip
call :check_http "%PAPERCLIP_URL%/api/health"
if not errorlevel 1 goto :paperclipup
set /a MOD=!TRIES! %% 10
if !MOD!==0 call :log       ... ainda aguardando (!TRIES!s / status=!STATUS!)
ping -n 2 127.0.0.1 >nul
goto :waitpaperclip

:paperclipup
call :log       OK - backend online em !TRIES!s.

REM 3) Frontend Dashboard + proxy local
if "%FRONTEND_ALREADY_UP%"=="0" (
    call :log [3/4] Subindo frontend dashboard em %DASHBOARD_URL%...
    start "Lead Machine Frontend" /D "%ROOT%" cmd /k "%PY_RUN% serve.py"
) else (
    call :log [3/4] Frontend dashboard reaproveitado.
)

REM Pequena espera para o serve.py abrir a porta.
ping -n 3 127.0.0.1 >nul

REM 4) Runner automatico (cron das buscas salvas)
REM 4) Runners automaticos (cron das buscas salvas)
call :log [4/4] Preparando runners automaticos...
taskkill /FI "WINDOWTITLE eq Lead Machine Runner*" /T /F >nul 2>&1

if "%START_GENERIC_RUNNER%"=="1" (
    call :log       Subindo runner generico...
    start "Lead Machine Runner Generic" /D "%ROOT%" cmd /k "%PY_RUN% agents\runner.py"
) else (
    call :log       Runner generico desligado. Para ligar: START_GENERIC_RUNNER=1 no .env
)

if "%START_APOSTAS_RUNNER%"=="1" (
    if exist "%ROOT%agents-apostas\runner_apostas.py" (
        call :log       Subindo runner de apostas...
        start "Lead Machine Runner Apostas" /D "%ROOT%" cmd /k "%PY_RUN% agents-apostas\runner_apostas.py"
    ) else (
        call :log [AVISO] Runner de apostas nao encontrado em agents-apostas\runner_apostas.py
    )
) else (
    call :log       Runner de apostas desligado. Para ligar: START_APOSTAS_RUNNER=1 no .env
)

REM Abre browser no frontend.
start "" "%DASHBOARD_URL%"

call :log
call :log =============================================================
call :log  TUDO PRONTO
call :log  Frontend:  %DASHBOARD_URL%
call :log  Backend:   %PAPERCLIP_URL%
call :log  Runners:   generico=%START_GENERIC_RUNNER% apostas=%START_APOSTAS_RUNNER%
call :log
call :log  Para parar tudo: rode stop.bat ou feche as janelas abertas.
call :log =============================================================
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
endlocal
exit /b 0

REM ==============================================================
REM SUB-ROTINAS
REM ==============================================================

:log
if "%~1"=="" (
    echo.
    echo.>> "%LOG%"
    exit /b 0
)
echo %*
echo [%time%] %* >> "%LOG%"
exit /b 0

:load_env
if not exist "%ROOT%.env" exit /b 0
for /f "tokens=1,* delims==" %%A in ('findstr /B /I /C:"PAPERCLIP_PORT=" /C:"DASHBOARD_PORT=" /C:"START_GENERIC_RUNNER=" /C:"START_APOSTAS_RUNNER=" "%ROOT%.env" 2^>nul') do (
    set "ENV_KEY=%%~A"
    set "ENV_VALUE=%%~B"
    if /i "!ENV_KEY!"=="PAPERCLIP_PORT" set "PAPERCLIP_PORT=!ENV_VALUE!"
    if /i "!ENV_KEY!"=="DASHBOARD_PORT" set "DASHBOARD_PORT=!ENV_VALUE!"
    if /i "!ENV_KEY!"=="START_GENERIC_RUNNER" set "START_GENERIC_RUNNER=!ENV_VALUE!"
    if /i "!ENV_KEY!"=="START_APOSTAS_RUNNER" set "START_APOSTAS_RUNNER=!ENV_VALUE!"
)
exit /b 0

:check_dep
where %~1 >nul 2>&1
if errorlevel 1 (
    call :log [ERRO] %~1 nao encontrado no PATH.
    call :log        Instalacao: %~2
    exit /b 1
)
for /f "delims=" %%v in ('where %~1') do (
    echo       OK %~1 em %%v
    echo [%time%]       OK %~1 em %%v >> "%LOG%"
    goto :check_dep_done
)
:check_dep_done
exit /b 0

:resolve_pnpm
set "PNPM_EXE="
set "PNPM_RUN="

for /f "delims=" %%P in ('where pnpm.cmd 2^>nul') do (
    set "PNPM_EXE=%%P"
    goto :pnpm_found
)

for /f "delims=" %%P in ('where pnpm 2^>nul') do (
    set "PNPM_EXE=%%P"
    goto :pnpm_found
)

if exist "%APPDATA%\npm\pnpm.cmd" (
    set "PNPM_EXE=%APPDATA%\npm\pnpm.cmd"
    goto :pnpm_found
)

where corepack.cmd >nul 2>&1
if not errorlevel 1 (
    set "PNPM_EXE=corepack"
    goto :pnpm_found
)

:pnpm_found
if not defined PNPM_EXE (
    echo [ERRO] pnpm nao encontrado no PATH e corepack nao esta disponivel.
    echo        Instalacao: npm install -g pnpm
    echo [%time%] [ERRO] pnpm nao encontrado no PATH e corepack nao esta disponivel. >> "%LOG%"
    echo [%time%]        Instalacao: npm install -g pnpm >> "%LOG%"
    exit /b 1
)

if /i "%PNPM_EXE%"=="corepack" (
    set "PNPM_RUN=corepack pnpm"
) else (
    set "PNPM_RUN="%PNPM_EXE%""
)
echo       OK pnpm = %PNPM_RUN%
echo [%time%]       OK pnpm = %PNPM_RUN% >> "%LOG%"
exit /b 0

:resolve_python
set "PYTHON_EXE="
set "PYTHON_ARGS="

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3.12"
    goto :python_found
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)

for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%P"
    goto :python_found
)

:python_found
if not defined PYTHON_EXE (
    echo [ERRO] Nenhum Python encontrado. Instale em https://python.org
    echo [%time%] [ERRO] Nenhum Python encontrado. Instale em https://python.org >> "%LOG%"
    exit /b 1
)

if /i "%PYTHON_EXE%"=="py" (
    set "PY_RUN=py %PYTHON_ARGS%"
) else (
    set "PY_RUN="%PYTHON_EXE%" %PYTHON_ARGS%"
)
echo       OK python = %PY_RUN%
echo [%time%]       OK python = %PY_RUN% >> "%LOG%"
exit /b 0

:run_python
"%PYTHON_EXE%" %PYTHON_ARGS% %*
exit /b %errorlevel%

:ensure_python_deps
call :run_python -c "import portalocker, requests, dotenv, apify_client" >nul 2>&1
if not errorlevel 1 exit /b 0

if "%CHECK_ONLY%"=="1" (
    echo [CHECK] Dependencias Python ausentes; start.bat instalara automaticamente ao iniciar.
    echo [%time%] [CHECK] Dependencias Python ausentes; start.bat instalara automaticamente ao iniciar. >> "%LOG%"
    exit /b 0
)

echo [AVISO] Dependencias Python ausentes. Instalando agents\requirements.txt...
echo [%time%] [AVISO] Dependencias Python ausentes. Instalando agents\requirements.txt... >> "%LOG%"
call :run_python -m pip install -r "%ROOT%agents\requirements.txt"
if errorlevel 1 (
    echo [ERRO] pip install falhou. Teste manual: %PY_RUN% -m pip install -r "%ROOT%agents\requirements.txt"
    echo [%time%] [ERRO] pip install falhou. Teste manual: %PY_RUN% -m pip install -r "%ROOT%agents\requirements.txt" >> "%LOG%"
    exit /b 1
)
exit /b 0

:is_port_listening
netstat -ano | findstr ":%~1" | findstr LISTENING >nul 2>&1
exit /b %errorlevel%

:check_http
set "STATUS=000"
curl.exe -s -o nul -w "%%{http_code}" %~1 > "%TEMP%\lm_check.txt" 2>nul
if exist "%TEMP%\lm_check.txt" set /p STATUS=<"%TEMP%\lm_check.txt"
if "%STATUS%"=="200" exit /b 0
if "%STATUS%"=="204" exit /b 0
if "%STATUS%"=="301" exit /b 0
if "%STATUS%"=="302" exit /b 0
exit /b 1

:timeout_paperclip
call :log
call :log ================================================================
call :log  [ERRO] Backend Paperclip nao respondeu em %MAX_TRIES%s.
call :log
call :log  Olhe a janela "Paperclip Backend" - ela tem o erro real.
call :log  Causas comuns:
call :log   - Primeira execucao: rode pnpm install em "%ROOT%paperclip"
call :log   - Porta %PAPERCLIP_PORT% em uso
call :log   - Erro de build/startup
call :log  Teste manual: cd /d "%ROOT%paperclip" ^&^& pnpm dev
call :log ================================================================
goto :fatal

:fatal
echo.
echo Log completo em: %LOG%
if "%CHECK_ONLY%"=="1" (
    endlocal
    exit /b 1
)
echo Pressione qualquer tecla para fechar...
pause >nul
endlocal
exit /b 1
