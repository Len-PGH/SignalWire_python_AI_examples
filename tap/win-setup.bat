@echo off

:: Check if Python is installed
echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please download and install Python 3 from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if Python is version 3
for /f "tokens=2" %%a in ('python --version') do set PYVERSION=%%a
if not "%PYVERSION:~0,2%" == "3." (
    echo This script requires Python 3, but you have Python %PYVERSION%.
    pause
    exit /b 1
)

:: Install pyaudio
echo Installing pyaudio...
python -m pip install pyaudio
if %errorlevel% neq 0 (
    echo Failed to install pyaudio. Please check the error message above.
    pause
    exit /b 1
)

:: Run the script
echo Running the script...
python rtp_listener.py
pause
