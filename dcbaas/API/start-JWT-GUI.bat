@echo off
setlocal EnableExtensions EnableDelayedExpansion
title JWT GUI launcher

rem === constants ===
set "SCRIPT_DIR=%~dp0"
set "TARGET_SCRIPT=jwt_gui.py"
set "REQ_FILE=requirements.txt"
set "ERR_LOG=last_error.log"
set "RUN_LOG=run.log"

rem === pretty colors ===
color 0A

call :banner "JWT GUI Launcher"

rem --- pick python ---
set "PY_EXE="
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
)

if not defined PY_EXE (
  for /f "delims=" %%P in ('where py 2^>NUL') do (
    set "PY_EXE=py -3"
    goto :py_found
  )
)

if not defined PY_EXE (
  for /f "delims=" %%P in ('where python 2^>NUL') do (
    set "PY_EXE=python"
    goto :py_found
  )
)

:py_found
if not defined PY_EXE (
  call :error "Geen Python gevonden. Installeer Python 3.10+ of activeer je venv."
  goto :end_fail
)

rem --- ensure requirements ---
pushd "%SCRIPT_DIR%"
if exist "%REQ_FILE%" (
  rem check a few critical modules; if any missing, run pip install -r requirements.txt
  %PY_EXE% -c "import sys;mods=['ttkbootstrap','jwcrypto','cryptography','requests','jwt'];import importlib;missing=[m for m in mods if importlib.util.find_spec(m) is None];sys.exit(len(missing)!=0)"
  if errorlevel 1 (
    call :info "Benodigde packages ontbreken → pip install -r requirements.txt"
    %PY_EXE% -m pip install -r "%REQ_FILE%" 1>>"%RUN_LOG%" 2>>"%ERR_LOG%"
    if errorlevel 1 (
      call :error "Installatie van dependencies is mislukt."
      if exist "%ERR_LOG%" (
        echo --- Laatste fouten (%ERR_LOG%) ---
        type "%ERR_LOG%" | more
      )
      goto :end_fail
    )
  )
) else (
  call :warn "Geen requirements.txt gevonden — ik probeer toch te starten."
)

rem --- run app ---
if not exist "%TARGET_SCRIPT%" (
  call :error "Bestand %TARGET_SCRIPT% niet gevonden in %SCRIPT_DIR%"
  goto :end_fail
)

call :info "Start: %TARGET_SCRIPT%"
del "%ERR_LOG%" 2>NUL
%PY_EXE% "%TARGET_SCRIPT%" 1>>"%RUN_LOG%" 2>"%ERR_LOG%"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  call :error "De applicatie sloot af met exitcode %EC%."
  if exist "%ERR_LOG%" (
    echo.
    echo --- Details uit %ERR_LOG% ---
    type "%ERR_LOG%" | more
  ) else (
    echo Geen foutlog gevonden. Mogelijk trad de fout op voor logging.
  )
  echo.
  goto :end_fail
)

call :ok "Klaar. Programma werd netjes afgesloten."
goto :end_ok

:banner
echo =============================================================
echo   %~1
echo =============================================================
goto :eof

:info
echo [INFO] %~1
goto :eof

:warn
echo [WAARSCHUWING] %~1
goto :eof

:error
echo [FOUT] %~1
goto :eof

:ok
echo [OK] %~1
goto :eof

:end_fail
echo.
echo Druk op een toets om dit venster te sluiten...
pause >NUL
popd
endlocal
exit /b 1

:end_ok
echo.
echo Druk op een toets om dit venster te sluiten...
pause >NUL
popd
endlocal
exit /b 0
