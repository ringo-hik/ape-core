#!/bin/bash
echo "APE (Agentic Pipeline Engine) Setup Script"
echo "========================================"

# Create and activate virtual environment
if [ ! -d "ape-venv" ]; then
    echo "Creating virtual environment..."
    python -m venv ape-venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Please ensure Python is correctly installed."
        exit 1
    fi
fi

echo "Activating virtual environment..."
source ape-venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Warning: Some packages failed to install. Certain packages may be restricted in internal networks."
        echo "Attempting to install essential packages individually..."
        
        # Install essential packages individually
        pip install -q python-dotenv requests fastapi uvicorn pydantic
        pip install -q python-multipart tqdm
        
        # Vector database and embedding packages (allow failures)
        pip install -q numpy || echo "Warning: numpy installation failed"
        pip install -q chromadb || echo "Warning: chromadb installation failed"
        pip install -q sentence-transformers || echo "Warning: sentence-transformers installation failed"
        
        # Try installing internal network compatible PyTorch version
        pip install -q torch==1.13.1 || echo "Warning: torch installation failed"
        
        # AI/ML related libraries (allow failures)
        pip install -q typing-extensions || echo "Warning: typing-extensions installation failed"
        pip install -q langchain || echo "Warning: langchain installation failed" 
        pip install -q langgraph || echo "Warning: langgraph installation failed"
    fi
else
    echo "Error: requirements.txt file not found."
    exit 1
fi

# Environment file setup
echo "Setting up environment file..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ".env file copied from .env.example."
        
        # Configure basic environment variables
        echo "Setting up network mode. Default is 'external'."
        read -p "Network mode (internal/external/hybrid): " network_mode
        network_mode=${network_mode:-external}
        
        # Modify .env file
        sed -i "s/NETWORK_MODE=.*/NETWORK_MODE=$network_mode/" .env
        
        if [[ "$network_mode" == "external" || "$network_mode" == "hybrid" ]]; then
            read -p "OpenRouter API key: " openrouter_key
            if [ ! -z "$openrouter_key" ]; then
                sed -i "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$openrouter_key/" .env
            fi
        fi
        
        if [[ "$network_mode" == "internal" || "$network_mode" == "hybrid" ]]; then
            read -p "Internal LLM endpoint: " internal_endpoint
            internal_endpoint=${internal_endpoint:-http://internal-llm-service/api}
            sed -i "s|INTERNAL_LLM_ENDPOINT=.*|INTERNAL_LLM_ENDPOINT=$internal_endpoint|" .env
            
            read -p "Internal LLM API key: " internal_key
            if [ ! -z "$internal_key" ]; then
                sed -i "s/INTERNAL_LLM_API_KEY=.*/INTERNAL_LLM_API_KEY=$internal_key/" .env
            fi
        fi
        
        echo ".env file configured successfully."
    else
        echo ".env.example file not found. Creating a new .env file."
        cat > .env << EOF
# Auto-generated .env file
NETWORK_MODE=external
API_HOST=0.0.0.0
API_PORT=8001
VERIFY_SSL=false
EOF
        echo "Basic .env file created. Modify as needed."
    fi
else
    echo ".env file already exists."
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/docs
mkdir -p data/chroma_db

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "To run the server:"
echo "python run.py or ./run_ape.sh"
echo ""
echo "Server will run at http://localhost:8001 by default"
echo "API documentation is available at http://localhost:8001/docs"
echo ""
echo "If you encounter any issues, check the log file:"
echo "tail -f server.log"
echo ""
echo "Network mode: ${network_mode:-external}"
echo "======================================"