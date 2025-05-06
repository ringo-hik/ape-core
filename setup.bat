@echo off
echo APE (Agentic Pipeline Engine) Setup Script for Internal Network
echo ========================================================

REM Set execution policy to bypass for this script
powershell -Command "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass" >nul 2>&1

REM Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.7 or higher and try again.
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ape-venv (
    echo Creating virtual environment...
    python -m venv ape-venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create virtual environment.
        echo Please ensure you have Python venv module available.
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call ape-venv\Scripts\activate.bat

REM Check for pip
pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip not found in virtual environment.
    echo Please ensure pip is available.
    exit /b 1
)

REM ========== INTERNAL NETWORK CONFIGURATION ==========
echo Setting up for INTERNAL NETWORK environment...

REM Try to use internal PyPI mirror if available
set INTERNAL_INDEX=--index-url http://pypi.internal.company/simple/ --trusted-host pypi.internal.company
echo Checking internal PyPI mirror...
pip install %INTERNAL_INDEX% --upgrade pip -q
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Internal PyPI mirror not available or not working.
    echo Will try direct installation. This may fail if Internet access is restricted.
    set INTERNAL_INDEX=
) else (
    echo Successfully connected to internal PyPI mirror.
)

REM Install essential packages individually with retry logic
echo Installing core packages...
call :install_package python-dotenv
call :install_package requests
call :install_package fastapi
call :install_package uvicorn
call :install_package pydantic
call :install_package python-multipart
call :install_package tqdm

echo Installing database packages...
call :install_package numpy
call :install_package chromadb
call :install_package sentence-transformers
call :install_package torch==1.13.1

echo Installing AI/ML libraries...
call :install_package typing-extensions
call :install_package langchain
call :install_package langgraph

REM Setup environment file
echo Setting up environment file...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo .env file created from template.
        
        REM Automatically set to internal mode
        powershell -Command "(Get-Content .env) -replace 'NETWORK_MODE=.*', 'NETWORK_MODE=internal' | Set-Content .env"
        echo NETWORK_MODE automatically set to 'internal'.
        
        echo Please update the internal LLM endpoint and API key in .env file.
        echo Configuring default internal settings...
        
        REM Set default internal settings
        powershell -Command "(Get-Content .env) -replace 'INTERNAL_LLM_ENDPOINT=.*', 'INTERNAL_LLM_ENDPOINT=http://internal-llm-service/api' | Set-Content .env"
        echo INTERNAL_LLM_ENDPOINT set to default value.
        echo You should edit the .env file to set the correct endpoint.
    ) else (
        echo Creating new .env file with internal configuration...
        (
            echo # APE Core environment file for internal network
            echo NETWORK_MODE=internal
            echo API_HOST=0.0.0.0
            echo API_PORT=8001
            echo VERIFY_SSL=false
            echo.
            echo # Internal LLM settings
            echo INTERNAL_LLM_ENDPOINT=http://internal-llm-service/api
            echo INTERNAL_LLM_API_KEY=your-internal-api-key
            echo INTERNAL_LLM_VERIFY_SSL=false
            echo INTERNAL_LLM_TIMEOUT=30
            echo INTERNAL_NETWORK_UNAVAILABLE_POLICY=fail
            echo.
            echo # Embedding model settings
            echo EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
            echo EMBEDDING_MODEL_PATH=models/all-MiniLM-L6-v2
            echo EMBEDDING_DIMENSION=384
            echo EMBEDDING_MAX_SEQ_LENGTH=512
        ) > .env
        echo New .env file created with internal network configuration.
    )
) else (
    echo .env file already exists.
    echo Setting it to internal mode...
    powershell -Command "(Get-Content .env) -replace 'NETWORK_MODE=.*', 'NETWORK_MODE=internal' | Set-Content .env"
    echo NETWORK_MODE updated to 'internal'.
)

REM Create data directories
echo Creating necessary directories...
if not exist data mkdir data
if not exist data\docs mkdir data\docs
if not exist data\chroma_db mkdir data\chroma_db
if not exist models mkdir models

echo.
echo ========================================================
echo Setup Complete for Internal Network Environment!
echo ========================================================
echo.
echo To run APE Core in internal network mode:
echo run_ape.bat --internal
echo.
echo Note: Make sure to update your .env file with correct
echo internal LLM endpoint and API key if needed.
echo ========================================================

REM Deactivate virtual environment
call ape-venv\Scripts\deactivate.bat
exit /b 0

REM ========== HELPER FUNCTIONS ==========
:install_package
setlocal
set PKG=%~1
echo Installing %PKG%...
pip install %INTERNAL_INDEX% %PKG% -q
if %ERRORLEVEL% NEQ 0 (
    echo Retrying %PKG% installation...
    pip install %PKG% -q
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Failed to install %PKG%. The application may not function correctly.
    ) else (
        echo %PKG% installed successfully on retry.
    )
) else (
    echo %PKG% installed successfully.
)
endlocal
goto :eof