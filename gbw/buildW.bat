@echo off
echo ========================================
echo   Bouwen van Wijchmaal.exe gestart...
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
  --name="Wijchmaal" ^
  --distpath "C:\d\OneDrive - TWEagle\MPS\MijnPythonScriptjes\gbw\output\Wijchmaal" ^
  --add-data "fonts;fonts" ^
  --add-data "pics;pics" ^
  --add-data "gblogo.ico;." ^
  "C:\d\OneDrive - TWEagle\MPS\MijnPythonScriptjes\gbw\qrgbw.pyw"

echo.
echo ========================================
echo ✅ EXE bestand gebouwd!
echo Locatie: output\Wijchmaal\Wijchmaal.exe
echo ========================================
pause
