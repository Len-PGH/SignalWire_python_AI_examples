@echo off

:: Check if Python is installed
echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% == 0 (
    :: Python is installed, check version
    for /f "tokens=2" %%a in ('python --version') do set PYVERSION=%%a
    if "!PYVERSION:~0,2!" == "3." (
        :: Python 3 is installed, get the path
        echo Python 3 is already installed. Locating executable...
        for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set PYTHON_PATH=%%i
    ) else (
        echo Existing Python is not version 3. Installing Python 3.9.6...
        goto :install_python
    )
) else (
    echo Python is not installed. Installing Python 3.9.6...
    goto :install_python
)
goto :install_dependencies

:install_python
:: Download and install Python based on system architecture
echo Determining system architecture...
if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
    set "INSTALLER_URL=https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe"
) else (
    set "INSTALLER_URL=https://www.python.org/ftp/python/3.9.6/python-3.9.6.exe"
)
set "INSTALLER_PATH=%TEMP%\python-installer.exe"

:: Download Python installer using bitsadmin
echo Downloading Python installer from %INSTALLER_URL%...
bitsadmin /transfer "PythonInstaller" /download /priority normal "%INSTALLER_URL%" "%INSTALLER_PATH%"

:: Install Python silently for the current user
echo Installing Python...
"%INSTALLER_PATH%" /quiet InstallAllUsers=0 PrependPath=1
if %errorlevel% neq 0 (
    echo Error: Python installation failed.
    del "%INSTALLER_PATH%"
    pause
    exit /b 1
)

:: Clean up installer
del "%INSTALLER_PATH%"

:: Set the path to the newly installed Python
set "PYTHON_PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python39\python.exe"
if not exist "%PYTHON_PATH%" (
    echo Error: Python executable not found at %PYTHON_PATH%. Installation may have failed.
    pause
    exit /b 1
)
echo Python 3.9.6 installed successfully.

:install_dependencies
:: Ensure pip is available and install dependencies
echo Ensuring pip is installed and installing pyaudio...
"%PYTHON_PATH%" -m pip install pyaudio
if %errorlevel% neq 0 (
    echo Error: Failed to install pyaudio. Attempting to install pip...
    :: Download and run get-pip.py if pip is missing
    set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
    set "GET_PIP_PATH=%TEMP%\get-pip.py"
    bitsadmin /transfer "GetPip" /download /priority normal "%GET_PIP_URL%" "%GET_PIP_PATH%"
    "%PYTHON_PATH%" "%GET_PIP_PATH%"
    del "%GET_PIP_PATH%"
    :: Retry installing pyaudio
    "%PYTHON_PATH%" -m pip install pyaudio
    if %errorlevel% neq 0 (
        echo Error: Failed to install pyaudio even after installing pip. Please check your internet connection or Python installation.
        pause
        exit /b 1
    )
)

:: Notify user of success
echo Setup complete. Python and pip are installed, and pyaudio is ready.

:: Optionally run a Python script (uncomment and modify as needed)
:: echo Running your script...
:: "%PYTHON_PATH%" "your_script.py"

pause
exit /b 0
