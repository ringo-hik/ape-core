@echo off
echo APE (Agentic Pipeline Engine) Setup Script
echo ========================================

REM Check if virtual environment exists
if not exist ape-venv (
    echo Creating virtual environment...
    python -m venv ape-venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment. Please ensure Python is correctly installed.
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call ape-venv\Scripts\activate.bat

echo Upgrading pip...
pip install --upgrade pip

echo Installing dependencies...
if exist requirements.txt (
    echo Installing packages from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Warning: Some packages failed to install. Installing essential packages individually...
        
        echo Installing basic packages...
        pip install -q python-dotenv requests fastapi uvicorn pydantic
        pip install -q python-multipart tqdm
        
        echo Installing vector database packages...
        pip install -q numpy || echo Warning: numpy installation failed
        pip install -q chromadb || echo Warning: chromadb installation failed
        pip install -q sentence-transformers || echo Warning: sentence-transformers installation failed
        
        echo Installing AI/ML libraries...
        pip install -q typing-extensions || echo Warning: typing-extensions installation failed
        pip install -q langchain || echo Warning: langchain installation failed
        pip install -q langgraph || echo Warning: langgraph installation failed
    )
) else (
    echo Error: requirements.txt file not found.
    echo Please create a requirements.txt file and run this script again.
    exit /b 1
)

echo Setting up environment file...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo .env file copied from .env.example.
        echo Please edit the .env file to configure your settings.
        echo Particularly, set the NETWORK_MODE to "internal" for internal network deployment.
    ) else (
        echo .env.example file not found. Creating a basic .env file...
        echo # Auto-generated .env file > .env
        echo NETWORK_MODE=external >> .env
        echo API_HOST=0.0.0.0 >> .env
        echo API_PORT=8001 >> .env
        echo VERIFY_SSL=false >> .env
        echo Basic .env file created. Please edit it to configure your settings.
    )
) else (
    echo .env file already exists.
)

echo Creating necessary directories...
if not exist data\docs mkdir data\docs
if not exist data\chroma_db mkdir data\chroma_db

echo.
echo ======================================
echo Installation Complete!
echo ======================================
echo.
echo To run the server:
echo python run.py --mode [internal^|external]
echo.
echo For internal network: python run.py --mode internal
echo For external network: python run.py --mode external (default)
echo.
echo Debug mode: python run.py --debug
echo.
echo Server will run at http://localhost:8001 by default
echo API documentation is available at http://localhost:8001/docs
echo ======================================