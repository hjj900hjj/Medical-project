@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" cli.py %*
  goto done
)
python --version >nul 2>&1
if not errorlevel 1 (
  python cli.py %*
  goto done
)
py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 cli.py %*
  goto done
)
echo Python 3 was not found. Install Python 3 and add it to PATH.
cmd /c exit 1

:done
set "cli_exit=%errorlevel%"
pause
exit /b %cli_exit%
