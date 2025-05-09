# APE (Agentic Pipeline Engine)

온프레미스 환경에서 동작하는 Agentic Pipeline Engine 시스템

## 개요

APE(Agentic Pipeline Engine)는 온프레미스 환경에서 동작하는 AI Agent 시스템입니다. 각 Agent는 독립적인 원자적 동작을 보장하며, 복잡한 워크플로우를 구성할 수 있습니다.

## 주요 기능

- **API 서버**: FastAPI 기반 RESTful API 서비스
- **LLM 서비스**: 내부망/외부망 연결 지원, 다양한 LLM 공급자 지원
- **RAG 에이전트**: 문서 검색 및 지식 증강 기능
- **벡터 저장소**: ChromaDB 기반 임베딩 저장 및 검색

## 시스템 요구사항

- Python 3.7 이상
- 인터넷 연결 (외부 LLM API 사용 시)
- 최소 4GB RAM

## 설치 및 실행

### 환경 설정

1. 저장소 클론 및 디렉토리 이동:
    ```
    git clone https://github.com/example/ape-core.git
    cd ape-core
    ```

2. 환경 변수 설정:
    ```
    cp .env.example .env
    ```
    `.env` 파일을 편집하여 필요한 API 키 및 설정을 추가합니다.
    
    **참고**: 데이터베이스 URI에 특수 문자(`@`, `:`, `/` 등)가 포함된 사용자 이름이나 비밀번호가 있는 경우, 자동으로 URL 인코딩이 적용됩니다.
    
    예시:
    ```
    # .env 파일
    SWDP_DB_URI=postgresql://user@name:p@ssw0rd@localhost:5432/swdp_db
    ```
    
    위 설정은 내부적으로 다음과 같이 변환됩니다:
    ```
    postgresql://user%40name:p%40ssw0rd@localhost:5432/swdp_db
    ```

### 실행 방법

제공된 실행 스크립트를 사용하여 서버를 실행합니다:

```bash
# 외부망 모드로 실행 (기본값)
./run_ape.sh

# 내부망 모드로 실행
./run_ape.sh --internal

# 디버그 모드 활성화
./run_ape.sh --debug

# 내부망 모드 + 디버그 모드
./run_ape.sh --internal --debug
```

또는 직접 Python 스크립트 실행:

```bash
# 외부망 모드로 실행 (기본값)
python run.py

# 내부망 모드로 실행
python run.py --mode internal

# 디버그 모드 활성화
python run.py --debug

# 도움말 표시
python run.py --help
```

기본적으로 서버는 `http://localhost:8001`에서 실행됩니다.

## API 엔드포인트

### 기본 엔드포인트

- `GET /`: API 정보
- `GET /health`: 서비스 상태 확인
- `GET /models`: 사용 가능한 모델 목록

### 에이전트 엔드포인트

- `GET /agents`: 에이전트 목록 조회
- `POST /agents/rag`: RAG 에이전트 실행
- `GET /agents/status/{agent_id}`: 에이전트 상태 조회

### 직접 쿼리 엔드포인트

- `POST /query`: LLM 직접 쿼리

## 에이전트 사용 예시

### RAG 에이전트 호출

```bash
curl -X POST http://localhost:8001/agents/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "APE(Agentic Pipeline Engine) 시스템에 대해 설명해주세요",
    "streaming": false
  }'
```

## 내부망/외부망 연결

APE는 내부망/외부망 설정을 완전히 분리하여 빌드 모드에 따라 다른 설정을 사용합니다:

### 네트워크 모드

- **외부망 모드**: 개발 및 테스트용 모드로, OpenRouter 등 외부 LLM API를 사용합니다.
- **내부망 모드**: 실제 배포 환경용 모드로, 내부망 LLM 서비스를 사용합니다.

### 자동 전환 기능

각 네트워크 모드에서도 장애 발생 시 자동 전환 기능을 제공합니다:

1. 내부망 모드에서 내부 LLM API 연결 실패 시:
   - 내부망 모드(strict)에서는 실패 처리
   - 내부망 모드(일반)에서는 외부망으로 자동 전환 시도
   
2. 외부망 모드에서 외부 LLM API 연결 실패 시:
   - 외부망 모드(strict)에서는 실패 처리
   - 외부망 모드(일반)에서는 다른 외부망 제공자로 자동 전환 시도

`.env` 파일 또는 실행 시 `--mode` 인자를 통해 네트워크 모드를 설정할 수 있습니다.

## 테스트

통합 테스트 실행:

```
cd tests
./run_tests.sh
```

테스트 옵션:
- `--local`: 로컬 테스트만 실행 (기본)
- `--external`: 외부망 연결 테스트 실행
- `--internal`: 내부망 연결 테스트 실행
- `--all`: 모든 테스트 실행

## 파일 구조

```
ape-core/
├── main.py              # 메인 진입점
├── run.py               # 서버 실행 스크립트
├── run_ape.sh           # 실행 쉘 스크립트
├── src/                 # 소스 코드
│   ├── core/            # 핵심 모듈
│   │   ├── config.py           # 설정 관리
│   │   ├── llm_service.py      # LLM 서비스 
│   │   ├── network_manager.py  # 네트워크 관리
│   │   └── router.py           # API 라우터
│   └── agents/          # 에이전트 모듈
│       ├── agent_manager.py    # 에이전트 관리
│       └── rag_agent.py        # RAG 에이전트
├── config/              # 설정 파일
│   ├── settings.json           # 시스템 설정
│   ├── models_internal.py      # 내부망 모델 설정
│   ├── models_external.py      # 외부망 모델 설정
│   └── network_config.py       # 네트워크 설정
├── data/                # 데이터 파일
│   ├── docs/                   # 문서 파일
│   └── chroma_db/              # 벡터 DB 저장소
└── tests/               # 테스트 코드
    ├── test_suite.py           # 통합 테스트
    └── test_config.json        # 테스트 설정
```

## 개발 가이드

### 새로운 에이전트 추가

1. `src/agents/` 디렉토리에 새 에이전트 클래스 파일 생성
2. `src/agents/agent_manager.py` 파일에 에이전트 등록
3. `config/settings.json` 파일의 `agents.available` 목록에 추가

### 설정 변경

`config/settings.json` 파일을 통해 시스템 설정 변경:

- API 서버 설정
- LLM 서비스 설정
- 벡터 저장소 설정
- 임베딩 모델 설정
- 문서 처리 설정
- 검색 설정

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 LICENSE 파일을 참조하세요.