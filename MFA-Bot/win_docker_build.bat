@echo off
REM ===============================================================
REM Batch Script to Build Docker Image and Manage Containers
REM ===============================================================

REM Configuration: Set the wait time (in seconds) after starting a container
set WAIT_TIME=5

REM Step 1: Build the Docker image
echo.
echo ============================================
echo Building Docker image 'mfa-bot-image'...
echo ============================================
docker build -t mfa-bot-image .

REM Check if the build was successful
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Docker build failed. Please check the Dockerfile and try again.
    pause
    exit /b %ERRORLEVEL%
)

REM Step 2: Display the menu for user choice
:menu
echo.
echo ============================================
echo                Main Menu
echo ============================================
echo 1. Spin off a new container
echo 2. Start an existing container
echo 3. Exit
echo ============================================
set /p choice=Enter your choice (1, 2, or 3): 

REM Handle user choice
if "%choice%"=="1" goto run_new_container
if "%choice%"=="2" goto start_existing_container
if "%choice%"=="3" goto end

echo.
echo Invalid choice. Please enter 1, 2, or 3.
goto menu

REM ===============================================================
REM Option 1: Spin off a new container
REM ===============================================================
:run_new_container
echo.
echo ============================================
echo         Spinning Off a New Container
echo ============================================

REM Prompt for container name with a default value
set /p containerName=Enter name for the new container (default: mfa-bot-container): 

REM Assign default name if none provided
if "%containerName%"=="" set containerName=mfa-bot-container

REM Check if a container with the given name already exists
docker ps -a --format "{{.Names}}" | findstr /I /C:"%containerName%" >nul
IF %ERRORLEVEL% EQU 0 (
    echo.
    echo A container named '%containerName%' already exists.
    echo Please choose a different name or remove the existing container.
    pause
    goto menu
)

REM Run the new container interactively with Bash shell
echo.
echo Running a new container '%containerName%' with Bash shell...
docker run -it --name %containerName% mfa-bot-image bash

goto menu

REM ===============================================================
REM Option 2: Start an Existing Container
REM ===============================================================
:start_existing_container
echo.
echo ============================================
echo        Starting an Existing Container
echo ============================================

REM Retrieve and list all containers based on 'mfa-bot-image'
echo.
echo Fetching list of existing containers based on 'mfa-bot-image'...
echo.

REM Initialize counter
setlocal enabledelayedexpansion
set i=1

REM Clear any previous container variables
for /L %%G in (1,1,1000) do (
    set "container%%G="
)

REM Loop through each container name and display with a number
for /f "tokens=*" %%a in ('docker ps -a --filter "ancestor=mfa-bot-image" --format "{{.Names}}"') do (
    set "container!i!=%%a"
    echo !i!. %%a
    set /a i+=1
)

REM Calculate the total number of containers found
set max=%i%

REM If no containers are found, inform the user and return to menu
if %max% EQU 1 (
    echo.
    echo No existing containers found for image 'mfa-bot-image'.
    echo Returning to the main menu.
    pause
    endlocal
    goto menu
)

REM Adjust max to reflect actual number of containers
set /a max-=1

REM Prompt user to select a container to start
echo.
set /p selection=Enter the number of the container to start: 

REM Validate the user's selection
set /a valid=0
if "%selection%"=="" goto invalid_selection
REM Check if the input is a number
set /a num=%selection% >nul 2>&1
IF %ERRORLEVEL% NEQ 0 goto invalid_selection
REM Check if the number is within the valid range
if %selection% GEQ 1 if %selection% LEQ %max% set valid=1

if %valid% NEQ 1 goto invalid_selection

REM Retrieve the container name based on user selection
call set container=%%container%selection%%%%

REM Check if the container is already running
docker ps --format "{{.Names}}" | findstr /I /C:"%container%" >nul
IF %ERRORLEVEL% NEQ 0 (
    REM Start the container if it's not running
    echo.
    echo Starting container '%container%'...
    docker start %container%
    IF %ERRORLEVEL% NEQ 0 (
        echo.
        echo Failed to start container '%container%'.
        pause
        endlocal
        goto menu
    )
) ELSE (
    echo.
    echo Container '%container%' is already running.
)

REM Wait for the container to initialize
echo.
echo Waiting %WAIT_TIME% seconds for the container to initialize...
timeout /t %WAIT_TIME% /nobreak >nul

REM Open a Bash shell in the running container
echo.
echo Opening Bash shell in container '%container%'...
docker exec -it %container% bash

echo.
echo Returned from Bash shell in container '%container%'.
pause
endlocal
goto menu

REM ===============================================================
REM Handle Invalid Selection
REM ===============================================================
:invalid_selection
echo.
echo Invalid selection. Please enter a valid number between 1 and %max%.
pause
endlocal
goto menu

REM ===============================================================
REM End of Script
REM ===============================================================
:end
echo.
echo ============================================
echo              Operation Completed
echo ============================================
pause
exit /b 0
