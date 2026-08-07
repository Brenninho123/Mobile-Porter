@echo off
setlocal

set PYTHON=python
set VENV_DIR=venv

where %PYTHON% >nul 2>nul
if errorlevel 1 (
    echo Python not found in PATH.
    exit /b 1
)

if not exist %VENV_DIR% (
    echo Creating virtual environment...
    %PYTHON% -m venv %VENV_DIR%
)

call %VENV_DIR%\Scripts\activate.bat

if exist requirements.txt (
    echo Installing dependencies...
    pip install -r requirements.txt --quiet
)

echo Starting Mobile-Porter...
python source\Main.py %*

endlocal
