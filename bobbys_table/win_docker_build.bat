@echo off
REM ===============================================================
REM Batch Script to Build Docker Image and Manage Containers
REM Options:
REM   1) Create a new container
REM   2) Start an existing container
REM   3) List and stop a running container
REM   4) Exit
REM ===============================================================

REM Enable delayed variable expansion
setlocal EnableDelayedExpansion

REM Configuration: Wait time (in seconds) for container readiness
set "WAIT_TIME=5"

REM Configuration: Maximum number of tries to start a container
set "MAX_TRIES=4"

REM Step 1: Build the Docker image
echo.
echo ============================================
echo Building Docker image 'bobbys_table_image'...
echo ============================================
docker build -t "bobbys_table_image" .
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Docker build failed. Please check the Dockerfile and try again.
    pause
    endlocal
    exit /b %ERRORLEVEL%
)

REM Main Menu
:menu
echo.
echo ============================================
echo              Main Menu
echo ============================================
echo 1. Create a new container
echo 2. Start an existing container
echo 3. List and stop a running container
echo 4. Exit
echo ============================================
set /p choice=Enter your choice (1, 2, 3, or 4): 

if "%choice%"=="1" goto create_new_container
if "%choice%"=="2" goto start_container_main
if "%choice%"=="3" goto stop_container_main
if "%choice%"=="4" goto end_script

echo.
echo Invalid choice. Please enter 1, 2, 3, or 4.
goto menu

REM ===============================================================
REM Option 1: Create a New Container
REM ===============================================================
:create_new_container
echo.
echo ============================================
echo         Create a New Container
echo ============================================
set /p containerName=Enter name for the new container (default: bobbys_table_container): 

if "%containerName%"=="" set "containerName=bobbys_table_container"

echo Checking if container name '%containerName%' is already used...
docker ps -a --format "{{.Names}}" | findstr /I /C:"%containerName%" >nul
if %ERRORLEVEL%==0 (
    echo.
    echo A container named '%containerName%' already exists.
    echo Please choose another name or remove the existing container.
    pause
    goto menu
)

echo.
echo Creating and running container '%containerName%' with Bash shell...
docker run -it --name "%containerName%" "bobbys_table_image" bash

goto menu

REM ===============================================================
REM Option 2: Start an Existing Container
REM (Lists ALL Containers, then multi-try start)
REM ===============================================================
:start_container_main
echo.
echo ============================================
echo    Start an Existing Container (All)
echo ============================================

echo.
echo Retrieving all containers on the system...
echo.

set /a count=1

FOR /L %%X IN (1,1,1000) DO (
    set "container%%X="
)

FOR /f "usebackq tokens=* delims=" %%A IN (`docker ps -a --format "{{.Names}}"`) DO (
    set "container!count!=%%A"
    echo !count!. %%A
    set /a count+=1
)

if %count%==1 (
    echo.
    echo No containers exist on this system.
    pause
    goto menu
)

set /a max=%count%-1
echo.
set /p selection=Enter the number of the container to start: 

set /a check=0
if "%selection%"=="" goto invalid_choice

set /a numeric=%selection% >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto invalid_choice

if %selection% GEQ 1 if %selection% LEQ %max% set /a check=1

if %check%==0 goto invalid_choice

call set "chosen=%%container%selection%%%%"

echo.
echo Checking if container '%chosen%' is running...
docker ps --format "{{.Names}}" | findstr /I /C:"%chosen%" >nul
if %ERRORLEVEL%==0 (
    echo.
    echo Container '%chosen%' is already running.
    goto container_running
)

echo.
echo Container '%chosen%' is not running. We will try to start it.

REM Attempt multiple tries
set /a tries=1

:start_docker_loop
if %tries% GTR %MAX_TRIES% (
    echo.
    echo We have tried %MAX_TRIES% times to start '%chosen%' without success.
    echo Returning to main menu.
    pause
    goto cleanup_list
)

echo.
echo Try #%tries%: Starting '%chosen%'...
docker start "%chosen%" >start_stdout.txt 2>start_stderr.txt
if %ERRORLEVEL%==0 (
    echo Container '%chosen%' started successfully.
    type start_stdout.txt
    del start_stdout.txt
    del start_stderr.txt
    goto container_just_started
) else (
    echo Failed to start container '%chosen%' on try #%tries%.
    type start_stderr.txt
    del start_stdout.txt
    del start_stderr.txt
    set /a tries+=1
    echo Waiting %WAIT_TIME% seconds before next try...
    timeout /t %WAIT_TIME% /nobreak >nul
    goto start_docker_loop
)

:container_just_started
echo.
echo Waiting %WAIT_TIME% seconds for '%chosen%' to get ready...
timeout /t %WAIT_TIME% /nobreak >nul

echo Checking if '%chosen%' is running now...
docker ps --format "{{.Names}}" | findstr /I /C:"%chosen%" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Container '%chosen%' still not running after start attempt.
    echo Returning to menu.
    pause
    goto cleanup_list
)

:container_running
echo.
echo Opening Bash shell in container '%chosen%'...
docker exec -it "%chosen%" bash

echo.
echo Returned from Bash shell in container '%chosen%'.
pause
:cleanup_list
endlocal
goto menu

:invalid_choice
echo.
echo Invalid selection. Please pick a valid container number between 1 and %max%.
pause
endlocal
goto menu

REM ===============================================================
REM Option 3: List and Stop a **Running** Container
REM ===============================================================
:stop_container_main
echo.
echo ============================================
echo   List and Stop a Running Container
echo ============================================

echo.
echo Retrieving currently running containers...
echo.

setlocal enabledelayedexpansion
set /a sCount=1

FOR /L %%Z IN (1,1,1000) DO (
    set "runCont%%Z="
)

REM Only running containers
FOR /f "usebackq tokens=* delims=" %%R IN (`docker ps --format "{{.Names}}"`) DO (
    set "runCont!sCount!=%%R"
    echo !sCount!. %%R
    set /a sCount+=1
)

if %sCount%==1 (
    echo.
    echo No running containers on this system.
    pause
    endlocal
    goto menu
)

set /a sMax=%sCount%-1
echo.
set /p sPick=Enter the number of the running container to stop: 

set /a sCheck=0
if "%sPick%"=="" goto invalid_stop_choice

set /a numericStop=%sPick% >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto invalid_stop_choice

if %sPick% GEQ 1 if %sPick% LEQ %sMax% set /a sCheck=1

if %sCheck%==0 goto invalid_stop_choice

call set "stopName=%%runCont%sPick%%%%"

echo.
echo Attempting to stop container '%stopName%'...
docker stop "%stopName%" >stop_stdout.txt 2>stop_stderr.txt
if %ERRORLEVEL%==0 (
    echo Container '%stopName%' stopped successfully.
    type stop_stdout.txt
    del stop_stdout.txt
    del stop_stderr.txt
) else (
    echo Failed to stop container '%stopName%'.
    type stop_stderr.txt
    del stop_stdout.txt
    del stop_stderr.txt
)

pause
endlocal
goto menu

:invalid_stop_choice
echo.
echo Invalid selection. Must be between 1 and %sMax%.
pause
endlocal
goto menu

REM ===============================================================
REM Option 4: End
REM ===============================================================
:end_script
echo.
echo ============================================
echo           Operation Completed
echo ============================================
pause
endlocal
exit /b 0
