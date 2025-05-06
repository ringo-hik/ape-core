# AI Agent 시스템 체크리스트

이 문서는 온프레미스 AI Agent 시스템의 핵심 구성요소와 정상 작동을 위한 체크리스트를 제공합니다. 시스템이 손상되거나 변경되었을 때 빠르게 복구하기 위한 가이드입니다.

## 필수 디렉토리 구조

```
ai-agent/
├── config/                # 설정 디렉토리
│   ├── settings.json     # 기본 설정 파일
│   └── embedding_config.py # 임베딩 모델 설정
├── data/                  # 데이터 저장소
│   ├── chroma_db/        # 벡터 DB 저장소
│   └── docs/             # 문서 저장소
├── models/                # 임베딩 모델 디렉토리
├── src/                   # 소스 코드
│   ├── agents/           # 에이전트 구현
│   │   ├── base_interface.py  # 기본 에이전트 인터페이스
│   │   ├── agent_manager.py   # 에이전트 관리자
│   │   ├── agent_factory.py   # 에이전트 팩토리
│   │   └── rag_agent.py       # RAG 에이전트
│   ├── core/             # 핵심 모듈
│   │   ├── config.py        # 설정 로드
│   │   ├── llm_service.py   # LLM 서비스
│   │   ├── router.py        # API 라우터
│   │   └── requests_config.py # 요청 설정
│   ├── schema/           # JSON 스키마 정의
│   └── utils/            # 유틸리티 함수
├── .env                   # 환경 변수 파일
├── .env.example           # 환경 변수 예시
├── config.py              # 설정 모듈
├── main.py                # 진입점
├── requirements.txt       # 의존성 정의
└── run.py                 # 서버 실행 스크립트
```

## 필수 파일 체크리스트

| 파일 | 설명 | 복구 방법 |
|------|------|-----------|
| `config/settings.json` | 시스템 설정 파일 | `config/settings.json` 설정 기본값 복원 |
| `src/core/llm_service.py` | LLM 연동 서비스 | 기본 구현으로 복원 |
| `src/core/router.py` | API 라우터 정의 | 기본 구현으로 복원 |
| `src/agents/base_interface.py` | 에이전트 인터페이스 | 기본 인터페이스 구현 복원 |
| `src/agents/agent_manager.py` | 에이전트 관리자 | 기본 구현으로 복원 |
| `src/agents/rag_agent.py` | RAG 에이전트 구현 | 기본 구현으로 복원 |
| `main.py` | 시스템 진입점 | 기본 템플릿 복원 |
| `run.py` | 서버 실행 스크립트 | 기본 템플릿 복원 |

## 핵심 의존성

```
fastapi>=0.95.0
uvicorn>=0.21.1
requests>=2.28.0
python-dotenv>=1.0.0
pydantic>=1.10.0
chromadb>=0.4.18
langchain>=0.0.267
anthropic>=0.5.0
```

## 필수 환경 변수

```
# API 설정
API_HOST=0.0.0.0
API_PORT=8001

# LLM 설정
DEFAULT_MODEL=claude3-opus
ANTHROPIC_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# 벡터 DB 설정
VECTOR_DB_TYPE=chroma
VECTOR_DB_PATH=data/chroma_db

# 임베딩 모델 설정
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
```

## 시스템 복구 단계

시스템이 손상되었을 경우 다음 단계를 따르세요:

1. 버전 관리 시스템(git)에서 마지막 안정 버전으로 복원
   ```
   git checkout master
   git pull origin master
   ```

2. 가상 환경 재설정
   ```
   python -m venv axiom_venv  # WSL 내 리눅스 파일시스템
   source axiom_venv/bin/activate
   pip install -r requirements.txt
   ```

3. 환경 변수 검증
   ```
   cp .env.example .env
   # .env 파일 편집하여 필요한 API 키 및 설정 추가
   ```

4. 시스템 시작 및 상태 확인
   ```
   python run.py
   ```

5. 엔드포인트 검증
   ```
   curl http://localhost:8001/health
   ```

## 문제 해결

1. **백업 디렉토리로부터 복원**
   - `backup/` 디렉토리에서 필요한 파일 복사
   - 기존 손상 파일 교체

2. **설정 초기화**
   - `.env` 파일 재설정
   - `config/settings.json` 기본 설정 복원

3. **데이터 디렉토리 재생성**
   ```
   mkdir -p data/docs data/chroma_db
   ```

4. **의존성 다시 설치**
   ```
   pip install -r requirements.txt
   ```

5. **권한 문제**
   ```
   chmod +x run.py
   chmod +x setup.sh
   ```

## 정상 시스템 확인 방법

1. 서버 시작하기: `python run.py`
2. 상태 확인: `curl http://localhost:8001/health`
3. 에이전트 조회: `curl http://localhost:8001/agents`
4. RAG 기능 테스트: `curl -X POST http://localhost:8001/agents/rag -H "Content-Type: application/json" -d '{"query": "AI Agent 시스템에 대해 설명해주세요"}'`

## 핵심 클래스 및 모듈 의존 관계

- `main.py` → `src/core/router.py` → `src/agents/agent_manager.py` → `src/agents/rag_agent.py`
- `src/agents/base_interface.py` ← 모든 에이전트 상속
- `src/core/llm_service.py` ← 모든 에이전트에서 사용
- `src/utils/*.py` ← 다양한 모듈에서 공통 기능 사용