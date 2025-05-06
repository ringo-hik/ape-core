@echo off
echo APE (Agentic Pipeline Engine) Setup Script
echo ========================================

REM 가상환경 확인
if not exist ape-venv (
    echo Error: ape-venv 가상환경 디렉토리가 존재하지 않습니다.
    echo 가상환경을 먼저 생성하세요: python -m venv ape-venv
    exit /b 1
)

echo 가상환경 활성화 중...
call ape-venv\Scripts\activate.bat

echo 기본 패키지 설치 중...
pip install -q python-dotenv requests

echo LLM 및 API 서버 패키지 설치 중...
pip install -q fastapi uvicorn pydantic python-multipart tqdm

echo 벡터 데이터베이스 및 임베딩 패키지 설치 중...
pip install -q chromadb sentence-transformers numpy

echo LangChain 및 LangGraph 패키지 설치 중...
pip install -q langgraph langchain

echo 환경 파일 설정 중...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo .env 파일이 .env.example에서 복사되었습니다. 필요한 경우 수정하세요.
    ) else (
        echo .env.example 파일이 없습니다. .env 파일을 수동으로 생성해야 합니다.
    )
) else (
    echo .env 파일이 이미 존재합니다.
)

echo.
echo 설치 완료!
echo.
echo 서버 실행 방법:
echo python run.py
echo.
echo 서버는 기본적으로 http://localhost:8001 에서 실행됩니다.
echo API 문서는 http://localhost:8001/docs 에서 확인할 수 있습니다.