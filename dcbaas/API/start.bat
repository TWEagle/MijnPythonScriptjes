@echo off
setlocal EnableExtensions EnableDelayedExpansion
title DCB Tools launcher

rem === constants ===
set "SCRIPT_DIR=%~dp0"
set "REQ_FILE=requirements.txt"

color 0A
call :banner "DCB Tools Launcher"

rem --- pick python ---
set "PY_EXE="
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
)

if not defined PY_EXE (
  for /f "delims=" %%P in ('where py 2^>NUL') do set "PY_EXE=py -3"
)
if not defined PY_EXE (
  for /f "delims=" %%P in ('where python 2^>NUL') do set "PY_EXE=python"
)

if not defined PY_EXE (
  call :error "Geen Python gevonden. Installeer Python 3.10+ of activeer je venv."
  goto :end_fail
)

rem --- ensure requirements (best-effort) ---
pushd "%SCRIPT_DIR%"
if exist "%REQ_FILE%" (
  %PY_EXE% -c "import sys;mods=['ttkbootstrap','jwcrypto','cryptography','requests','jwt'];import importlib;missing=[m for m in mods if importlib.util.find_spec(m) is None];sys.exit(len(missing)!=0)"
  if errorlevel 1 (
    call :info "Dependencies installeren..."
    %PY_EXE% -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
      call :warn "Installatie van dependencies mislukte. Ik ga toch verder."
    )
  )
)

:menu
echo.
echo Welke tool wil je starten?
echo   [1] JWT GUI (jwt_gui.py)
echo   [2] Application GUI (application_gui.py)
echo   [3] Certificates GUI (certificates_gui.py)
echo   [Q] Afsluiten
set /p "choice=Maak je keuze: "
if /i "%choice%"=="1"  (set "TARGET=jwt_gui.py") else (
if /i "%choice%"=="2"  (set "TARGET=application_gui.py") else (
if /i "%choice%"=="3"  (set "TARGET=certificates_gui.py") else (
if /i "%choice%"=="Q"  goto :end_ok
goto :menu
)))

if not exist "%TARGET%" (
  call :error "%TARGET% niet gevonden in %SCRIPT_DIR%"
  goto :menu
)

call :info "Start: %TARGET%"
%PY_EXE% "%TARGET%"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  call :error "De applicatie sloot af met exitcode %EC%."
  echo.
  echo Mogelijke oorzaken:
  echo   - Ontbrekende modules (probeer: pip install -r requirements.txt)
  echo   - Onjuiste key-bestanden of paden
  echo   - Geen internet of endpoint onbereikbaar
  echo.
  goto :menu
)

echo.
call :ok "KLAAR — Programma is netjes afgesloten."
goto :menu

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
