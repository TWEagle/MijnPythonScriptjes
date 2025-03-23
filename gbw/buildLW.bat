@echo off
echo ========================================
echo   Bouwen van Linde-Wauberg.exe gestart...
echo ========================================

REM Stap 1: dependencies installeren
echo Installeren van dependencies vanuit requirements.txt...
pip install -r requirements.txt

REM Stap 2: PyInstaller aanroepen
echo Bouwen met PyInstaller...
pyinstaller ^
  --clean ^
  --onefile ^
  --windowed ^
  --icon="C:\d\OneDrive - TWEagle\MPS\MijnPythonScriptjes\gbw\gblogo.ico" ^
  --name="Linde-Wauberg" ^
  --distpath "C:\d\OneDrive - TWEagle\MPS\MijnPythonScriptjes\gbw\output\LindeWauberg" ^
  --add-data "fonts;fonts" ^
  --add-data "pics;pics" ^
  --add-data "gblogo.ico;." ^
  "C:\d\OneDrive - TWEagle\MPS\MijnPythonScriptjes\gbw\qrgblw.pyw"

echo.
echo ========================================
echo ✅ EXE bestand gebouwd!
echo Locatie: output\LindeWauberg\Linde-Wauberg.exe
echo ========================================
pause
