#!/bin/bash
# 내부망 환경 자동 설정 스크립트
# 외부망에서 개발하다가 내부망으로 배포할 때 사용

echo "APE Core 내부망 환경 자동 설정 스크립트"
echo "======================================"

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

# 필수 패키지 개별 설치 (내부망 최적화)
echo "필수 패키지 설치 중... (내부망 호환성 고려)"
pip install -q python-dotenv requests
pip install -q fastapi uvicorn~=0.21.1 pydantic~=1.10.7
pip install -q python-multipart tqdm typing-extensions
pip install -q numpy~=1.22.0

# 내부망 호환 가능한 AI 패키지 설치 시도
echo "내부망 호환 가능한 AI 패키지 설치 시도 중..."
pip install -q torch==1.13.1 || echo "Warning: torch 설치 실패"
pip install -q chromadb || echo "Warning: chromadb 설치 실패" 
pip install -q sentence-transformers || echo "Warning: sentence-transformers 설치 실패"
pip install -q langchain || echo "Warning: langchain 설치 실패"
pip install -q langgraph || echo "Warning: langgraph 설치 실패"

# 기본 환경 파일 생성
echo "내부망 환경 설정 파일 생성 중..."
cat > .env << EOF
# 내부망 환경 설정 (자동 생성됨)
NETWORK_MODE=internal
API_HOST=0.0.0.0
API_PORT=8001
API_TIMEOUT=120
API_STREAM=true

# 보안 설정
USE_SSL=false
VERIFY_SSL=false

# 내부망 LLM API 설정
INTERNAL_LLM_ENDPOINT=http://internal-llm-service/api
INTERNAL_LLM_API_KEY=your-internal-api-key
INTERNAL_LLM_VERIFY_SSL=false
INTERNAL_LLM_TIMEOUT=30

# 내부망 전용 설정
STRICT_NETWORK_SEPARATION=true
INTERNAL_NETWORK_ENABLED=true
EXTERNAL_NETWORK_ENABLED=false
DEFAULT_MODEL=internal-model

# 임베딩 모델 설정
EMBEDDING_MODEL_NAME=KoSimCSE-roberta
EMBEDDING_MODEL_PATH=models/KoSimCSE-roberta-multitask
EMBEDDING_DIMENSION=768
EMBEDDING_MAX_SEQ_LENGTH=512
EOF

echo "환경 변수 파일이 생성되었습니다. 필요에 따라 .env 파일을 직접 수정하세요."

# 필요한 디렉토리 생성
echo "필요한 디렉토리 생성 중..."
mkdir -p data/docs
mkdir -p data/chroma_db

echo ""
echo "======================================"
echo "내부망 환경 설정 완료!"
echo "======================================"
echo ""
echo "서버 실행 방법:"
echo "python run.py 또는 ./run_ape.sh"
echo ""
echo "서버는 기본적으로 http://localhost:8001 에서 실행됩니다."
echo "중요: 내부망 LLM 서비스 엔드포인트와 API 키를 설정했는지 확인하세요."
echo "      .env 파일을 열어 INTERNAL_LLM_ENDPOINT와 INTERNAL_LLM_API_KEY 값을 수정하세요."
echo ""
echo "네트워크 모드: internal (내부망 전용)"
echo "======================================"