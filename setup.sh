#!/bin/bash
echo "APE (Agentic Pipeline Engine) Setup Script"
echo "========================================"

# 가상환경 생성 및 활성화
if [ ! -d "ape-venv" ]; then
    echo "가상환경 생성 중..."
    python -m venv ape-venv
    if [ $? -ne 0 ]; then
        echo "Error: 가상환경 생성에 실패했습니다. Python이 올바르게 설치되어 있는지 확인하세요."
        exit 1
    fi
fi

echo "가상환경 활성화 중..."
source ape-venv/bin/activate

echo "Pip 업그레이드 중..."
pip install --upgrade pip

echo "Requirements 파일에서 의존성 설치 중..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Warning: 일부 패키지 설치에 실패했습니다. 내부망에서는 일부 패키지가 제한될 수 있습니다."
        echo "필수 패키지 개별 설치를 시도합니다..."
        
        # 필수 패키지 개별 설치
        pip install -q python-dotenv requests fastapi uvicorn pydantic
        pip install -q python-multipart tqdm
        
        # 벡터 데이터베이스 및 임베딩 패키지 (오류 허용)
        pip install -q numpy || echo "Warning: numpy 설치 실패"
        pip install -q chromadb || echo "Warning: chromadb 설치 실패"
        pip install -q sentence-transformers || echo "Warning: sentence-transformers 설치 실패"
        
        # 내부망 호환 가능한 PyTorch 버전 시도
        pip install -q torch==1.13.1 || echo "Warning: torch 설치 실패"
        
        # AI/ML 관련 라이브러리 (오류 허용)
        pip install -q typing-extensions || echo "Warning: typing-extensions 설치 실패"
        pip install -q langchain || echo "Warning: langchain 설치 실패" 
        pip install -q langgraph || echo "Warning: langgraph 설치 실패"
    fi
else
    echo "Error: requirements.txt 파일이 없습니다."
    exit 1
fi

# 환경 파일 설정
echo "환경 파일 설정 중..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ".env 파일이 .env.example에서 복사되었습니다."
        
        # 기본 환경 변수 설정
        echo "내부망/외부망 모드를 설정합니다. 기본값은 'external'입니다."
        read -p "네트워크 모드 (internal/external/hybrid): " network_mode
        network_mode=${network_mode:-external}
        
        # .env 파일 수정
        sed -i "s/NETWORK_MODE=.*/NETWORK_MODE=$network_mode/" .env
        
        if [[ "$network_mode" == "external" || "$network_mode" == "hybrid" ]]; then
            read -p "OpenRouter API 키: " openrouter_key
            if [ ! -z "$openrouter_key" ]; then
                sed -i "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$openrouter_key/" .env
            fi
        fi
        
        if [[ "$network_mode" == "internal" || "$network_mode" == "hybrid" ]]; then
            read -p "내부망 LLM 엔드포인트: " internal_endpoint
            internal_endpoint=${internal_endpoint:-http://internal-llm-service/api}
            sed -i "s|INTERNAL_LLM_ENDPOINT=.*|INTERNAL_LLM_ENDPOINT=$internal_endpoint|" .env
            
            read -p "내부망 LLM API 키: " internal_key
            if [ ! -z "$internal_key" ]; then
                sed -i "s/INTERNAL_LLM_API_KEY=.*/INTERNAL_LLM_API_KEY=$internal_key/" .env
            fi
        fi
        
        echo ".env 파일이 성공적으로 설정되었습니다."
    else
        echo ".env.example 파일이 없습니다. 새 .env 파일을 생성합니다."
        cat > .env << EOF
# 자동 생성된 .env 파일
NETWORK_MODE=external
API_HOST=0.0.0.0
API_PORT=8001
VERIFY_SSL=false
EOF
        echo "기본 .env 파일이 생성되었습니다. 필요에 따라 수정하세요."
    fi
else
    echo ".env 파일이 이미 존재합니다."
fi

# 필요한 디렉토리 생성
echo "필요한 디렉토리 생성 중..."
mkdir -p data/docs
mkdir -p data/chroma_db

echo ""
echo "======================================"
echo "설치 완료!"
echo "======================================"
echo ""
echo "서버 실행 방법:"
echo "python run.py 또는 ./run_ape.sh"
echo ""
echo "서버는 기본적으로 http://localhost:8001 에서 실행됩니다."
echo "API 문서는 http://localhost:8001/docs 에서 확인할 수 있습니다."
echo ""
echo "문제가 발생하면 로그 파일을 확인하세요:"
echo "tail -f server.log"
echo ""
echo "네트워크 모드: ${network_mode:-external}"
echo "======================================"