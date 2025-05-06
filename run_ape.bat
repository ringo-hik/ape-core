@echo off
REM APE (Agentic Pipeline Engine) Run Script

setlocal EnableDelayedExpansion

REM Default settings
set MODE=external
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
echo Running mode: %MODE%

REM Check if virtual environment exists
if not exist ape-venv (
    echo Error: Virtual environment not found.
    echo Please run setup.bat first to set up the environment.
    exit /b 1
)

REM Activate virtual environment
call ape-venv\Scripts\activate.bat

REM Run with appropriate parameters
if "%DEBUG%"=="true" (
    echo Debug mode enabled
    python run.py --mode %MODE% --debug
) else (
    python run.py --mode %MODE%
)

REM Deactivate virtual environment
deactivate

endlocal