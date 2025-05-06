@echo off
REM APE (Agentic Pipeline Engine) Run Script for Internal Network
REM Version 1.0

setlocal EnableDelayedExpansion

REM Default settings
set MODE=internal
set DEBUG=false

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--internal" (
    set MODE=internal
    shift
    goto :parse_args
)
if /i "%~1"=="--external" (
    set MODE=external
    shift
    goto :parse_args
)
if /i "%~1"=="--debug" (
    set DEBUG=true
    shift
    goto :parse_args
)
echo Unknown option: %1
echo Usage: %0 [--internal^|--external] [--debug]
exit /b 1
:end_parse

REM Display current mode
echo.
echo ========================================================
echo Running APE (Agentic Pipeline Engine) - %MODE% mode
echo ========================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.7+ and try again.
    exit /b 1
)

REM Check if virtual environment exists
if not exist ape-venv (
    echo Error: Virtual environment not found.
    echo Run setup.bat first to configure the environment.
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call ape-venv\Scripts\activate.bat

REM Verify python-dotenv is installed
python -c "import dotenv" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Warning: python-dotenv not found. Attempting to install...
    pip install python-dotenv -q
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install python-dotenv. Please install it manually.
        call ape-venv\Scripts\deactivate.bat
        exit /b 1
    )
    echo Successfully installed python-dotenv.
)

REM Set up log file
set LOGFILE=server.log
echo Starting server, logging to %LOGFILE%

REM Create log header
echo ========================================================>> %LOGFILE%
echo APE Core Server Started: %DATE% %TIME%>> %LOGFILE%
echo Network Mode: %MODE%>> %LOGFILE%
echo Debug Mode: %DEBUG%>> %LOGFILE%
echo ========================================================>> %LOGFILE%
echo.>> %LOGFILE%

REM Run with appropriate parameters
if "%DEBUG%"=="true" (
    echo Debug mode enabled. Detailed logs will be displayed.
    python run.py --mode %MODE% --debug
) else (
    echo Normal mode. Check %LOGFILE% for detailed logs.
    REM Redirect stdout/stderr to logfile and console
    python run.py --mode %MODE% 2>&1 | tee -a %LOGFILE%
    
    REM Check if tee command fails (not available on Windows by default)
    if %ERRORLEVEL% NEQ 0 (
        python run.py --mode %MODE% 2>> %LOGFILE%
    )
)

REM Deactivate virtual environment
call ape-venv\Scripts\deactivate.bat

echo.
echo APE Core server has been stopped.
echo.

endlocal