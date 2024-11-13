import sys
from cx_Freeze import setup, Executable

# Voeg extra bestanden toe
files = [
    'pics',  # map met uw afbeeldingen
    'fonts',  # map met uw font
    'sounds',  # map met uw geluiden
    'qrgbw.py',  # Python script
    'qrgb.py',  # Python script
    'aftelklok.py',  # Python script
    'gbwmenu.py'  # Python script
]

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [
    Executable('start.py', base=base)
]

setup(
    name='Gezinsbond Tool Selecteerder',
    version='0.1',
    description='Selecteerder voor de Gezinsbond Tool',
    options = {'build_exe': {'include_files': files}},
    executables = executables
)
