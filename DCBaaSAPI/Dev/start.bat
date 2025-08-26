@echo off
setlocal ENABLEEXTENSIONS

rem Ga naar de map waar dit .bat-bestand staat
cd /d "%~dp0"

rem --- Kies Python: probeer eerst py -3.13, dan py -3, dan python ---
set "PY_CMD="
py -3.13 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.13"
if not defined PY_CMD py -3 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD python -c "import sys" >nul 2>&1 && set "PY_CMD=python"

if not defined PY_CMD (
  echo [FOUT] Geen geschikte Python gevonden. Installeer Python 3 en probeer opnieuw.
  pause
  exit /b 1
)

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ=requirements.txt"

rem --- Maak venv als die nog niet bestaat ---
if not exist "%VENV_PY%" (
  echo [INFO] Virtuele omgeving niet gevonden. Aanmaken...
  %PY_CMD% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [FOUT] Kon virtuele omgeving niet aanmaken.
    pause
    exit /b 1
  )
)

rem --- Activeer venv ---
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [FOUT] Kon .venv niet activeren.
  pause
  exit /b 1
)

rem --- Upgrade pip (optioneel maar handig) ---
python -m pip install --upgrade pip >nul 2>&1

rem --- Installeer requirements indien aanwezig ---
if exist "%REQ%" (
  echo [INFO] Packages installeren uit %REQ% ...
  python -m pip install -r "%REQ%"
  if errorlevel 1 (
    echo [FOUT] Installatie van dependencies mislukt.
    pause
    exit /b 1
  )
)

rem --- Start de GUI ---
echo [INFO] Start jwt_gui.py ...
python "jwt_gui.py"
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% NEQ 0 (
  echo [FOUT] Het script is gestopt met exitcode %EXITCODE%.
) else (
  echo [KLAAR] Programma is netjes afgesloten.
)

pause
endlocal
