#!/bin/bash

# APE (Agentic Pipeline Engine) 목 테스트 실행 스크립트
#
# 이 스크립트는 실제 외부 서비스에 연결하지 않고 목(mock) 객체를 사용하여 테스트를 실행합니다.
# 서버를 실행하지 않아도 테스트할 수 있습니다.

# 현재 디렉토리 저장
CURRENT_DIR=$(pwd)

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 상위 디렉토리(프로젝트 루트)로 이동
cd ../..

# 환경 설정
echo "===== 테스트 환경 설정 ====="
export INTERNAL_LLM_ENDPOINT="http://internal-llm-service/api"
export INTERNAL_LLM_API_KEY="mock_internal_key"
export OPENROUTER_API_KEY="mock_openrouter_key"
export OPENROUTER_ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
export DEFAULT_MODEL="internal-model"

# 파이썬 가상 환경 설정
if [ -d "axiom_venv" ]; then
    echo "axiom_venv 가상환경을 활성화합니다..."
    source axiom_venv/bin/activate
elif [ -d "venv" ]; then
    echo "venv 가상환경을 활성화합니다..."
    source venv/bin/activate
elif [ -d "test_venv" ]; then
    echo "test_venv 가상환경을 활성화합니다..."
    source test_venv/bin/activate
else
    echo "가상환경을 찾을 수 없습니다. 필요한 패키지가 시스템에 설치되어 있는지 확인하세요."
    echo "필요한 패키지: python-dotenv, requests"
fi

# 필요한 패키지 설치 확인
pip install -q python-dotenv requests 2>/dev/null

# 테스트 모듈 실행
echo "===== LLM 서비스 목 테스트 실행 ====="
python -m unittest tests/mock_tests/test_llm_service.py

# 종료 코드 저장
EXIT_CODE=$?

# 원래 디렉토리로 돌아가기
cd "$CURRENT_DIR"

# 종료 코드 반환
exit $EXIT_CODE