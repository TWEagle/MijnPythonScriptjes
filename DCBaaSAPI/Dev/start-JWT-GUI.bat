@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python jwt_gui.py
pause
