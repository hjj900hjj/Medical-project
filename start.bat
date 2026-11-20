@echo off
cd /d "%~dp0"
if exist "..\screen-tutor\.venv\Scripts\python.exe" (
  "..\screen-tutor\.venv\Scripts\python.exe" cli.py
) else (
  py -3 cli.py
)
pause
