@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   FACELENS CLI - Windows Setup
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=python"
    ) else (
        echo ERROR: Python not found.
        echo Install Python 3.9+ from https://www.python.org/downloads/
        echo Make sure to tick "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

if not exist venv (
    echo [1/3] Creating virtual environment...
    %PYTHON% -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment already exists.
)

echo [2/3] Installing dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

if not exist .env (
    echo [3/3] Creating .env from template...
    copy .env.example .env >nul
    echo.
    echo NOTE: Open .env and set PRIVATE_KEY and CONTRACT_ADDRESS.
    echo (Copy the .env from your Linux server - it already has working values.)
) else (
    echo [3/3] .env already present.
)

echo.
echo ============================================
echo   SETUP COMPLETE
echo ============================================
echo.
echo Run a search:
echo   run.bat search --image "C:\path\to\person.jpg"
echo.
echo Show help:
echo   run.bat --help
echo.
pause